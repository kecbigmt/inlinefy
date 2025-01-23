#!/usr/bin/env python3
from bs4 import BeautifulSoup
import re
import argparse
import sys
from pathlib import Path

def calculate_specificity(selector):
    """
    CSSセレクタの詳細度を計算する
    返り値は (ID数, クラス数, 要素数) のタプル
    """
    # セレクタをクリーンアップ
    selector = selector.strip()
    
    # ID選択子の数 (#)
    a = len(re.findall(r'#[a-zA-Z0-9_-]+', selector))
    
    # クラス選択子 (.) と属性選択子 ([attr]) と疑似クラス (:) の数
    b = len(re.findall(r'\.[a-zA-Z0-9_-]+|\[[^\]]+\]|:[a-zA-Z0-9_-]+', selector))
    
    # 要素型選択子と疑似要素 (::) の数
    c = len(re.findall(r'[a-zA-Z0-9_-]+|::?[a-zA-Z0-9_-]+', selector)) - (a + b)
    
    return (a, b, max(c, 0))  # cが負になることを防ぐ

def extract_css_rules(css_text):
    # CSSルールを格納するリスト（順序を保持するため辞書ではなくリストを使用）
    css_rules = []
    
    # メディアクエリを除外するため、@mediaの外側のルールのみを処理
    main_css = re.sub(r'@media[^{]+\{(?:[^{}]|\{[^{}]*\})*\}', '', css_text)
    
    # CSSルールを解析
    rules = re.findall(r'([^{]+){([^}]+)}', main_css)
    
    for index, (selector_group, styles) in enumerate(rules):
        # カンマで区切られた複数のセレクタを処理
        for selector in selector_group.split(','):
            selector = selector.strip()
            if not selector:
                continue
                
            # スタイル属性をディクショナリに変換
            style_dict = {}
            for style in styles.split(';'):
                if ':' in style:
                    prop, value = style.split(':', 1)
                    style_dict[prop.strip()] = value.strip()
            
            # セレクタの詳細度を計算
            specificity = calculate_specificity(selector)
            
            css_rules.append({
                'selector': selector,
                'styles': style_dict,
                'specificity': specificity,
                'order': index  # 元のCSSでの出現順を保存
            })
    
    return css_rules

def compare_specificity(spec1, spec2):
    """
    詳細度を比較する
    spec1 > spec2 の場合は True、それ以外は False を返す
    """
    return spec1 > spec2

def merge_styles(current_styles, new_styles, current_specificity, new_specificity):
    """
    詳細度を考慮してスタイルをマージする
    """
    merged = current_styles.copy()
    
    for prop, value in new_styles.items():
        # 既存のプロパティが存在しない場合は新しい値を追加
        if prop not in current_styles:
            merged[prop] = value
        # 新しいスタイルの詳細度が高い場合は上書き
        elif compare_specificity(new_specificity, current_specificity):
            merged[prop] = value
        # 詳細度が同じ場合は新しい値で上書き（CSSの通常の挙動）
        elif new_specificity == current_specificity:
            merged[prop] = value
    
    return merged

def apply_inline_styles(html_text, css_rules):
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # bodyタグを取得
    body = soup.find('body')
    if not body:
        return str(soup)

    # 要素ごとに適用されるスタイルを管理する辞書
    element_styles = {}
    
    # 詳細度でソート（詳細度が同じ場合は元のCSSでの出現順を使用）
    css_rules.sort(key=lambda x: (x['specificity'], x['order']))
    
    # 各CSSルールに対して
    for rule in css_rules:
        try:
            # セレクタを使って要素をbody内から選択
            elements = body.select(rule['selector'])
            
            # 見つかった要素それぞれにスタイルを適用
            for element in elements:
                # 要素のIDを取得（または生成）
                element_id = id(element)
                
                if element_id not in element_styles:
                    # 既存のインラインスタイルを初期値として使用
                    existing_styles = {}
                    if element.get('style'):
                        for style_def in element['style'].split(';'):
                            if ':' in style_def:
                                prop, value = style_def.split(':', 1)
                                existing_styles[prop.strip()] = value.strip()
                    
                    element_styles[element_id] = {
                        'styles': existing_styles,
                        'specificity': (1, 0, 0)  # インラインスタイルの詳細度は最も高い
                    }
                
                # スタイルをマージ
                element_styles[element_id]['styles'] = merge_styles(
                    element_styles[element_id]['styles'],
                    rule['styles'],
                    element_styles[element_id]['specificity'],
                    rule['specificity']
                )
                element_styles[element_id]['specificity'] = rule['specificity']
        except Exception as e:
            print(f"Error processing selector {rule['selector']}: {str(e)}", file=sys.stderr)
            continue
    
    # 最終的なスタイルを要素に適用
    for element_id, style_info in element_styles.items():
        try:
            for element in soup.find_all(lambda tag: id(tag) == element_id):
                # 既存のインラインスタイルを取得
                existing_styles = {}
                if element.get('style'):
                    for style_def in element['style'].split(';'):
                        if ':' in style_def:
                            prop, value = style_def.split(':', 1)
                            existing_styles[prop.strip()] = value.strip()
                
                # 新しいスタイルと既存のスタイルをマージ
                merged_styles = {**style_info['styles'], **existing_styles}
                styles_list = [f"{prop}:{value}" for prop, value in merged_styles.items()]
                element['style'] = ';'.join(styles_list)
        except Exception as e:
            print(f"Error applying styles to element: {str(e)}", file=sys.stderr)
            continue
    
    # スタイルタグを処理（メディアクエリは残す）
    for style in soup.find_all('style'):
        if style.string and '@media' in style.string:
            try:
                # メディアクエリを抽出
                media_queries = re.findall(r'(@media[^{]+\{(?:[^{}]|\{[^{}]*\})*\})', style.string)
                if media_queries:
                    # メディアクエリのみを含む新しいスタイルタグを作成
                    style.string = '\n'.join(media_queries)
                else:
                    style.decompose()
            except Exception as e:
                print(f"Error processing media queries: {str(e)}", file=sys.stderr)
                continue
        else:
            style.decompose()
    
    return str(soup)

def convert_css_to_inline(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # スタイルタグからCSSを抽出
    css_text = ''
    for style in soup.find_all('style'):
        if style.string:
            css_text += style.string
    
    # CSSルールを抽出
    css_rules = extract_css_rules(css_text)
    
    # インラインスタイルを適用
    return apply_inline_styles(html_content, css_rules)

def main():
    parser = argparse.ArgumentParser(
        description='Convert CSS in style tags to inline styles within HTML files while preserving media queries.'
    )
    parser.add_argument(
        'input',
        type=str,
        help='Path to the input HTML file'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Path to the output HTML file (if not specified, output will be printed to stdout)'
    )

    args = parser.parse_args()

    try:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file '{args.input}' does not exist", file=sys.stderr)
            sys.exit(1)

        with open(input_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        converted_html = convert_css_to_inline(html_content)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(converted_html)
        else:
            print(converted_html)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

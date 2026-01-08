// ===================================
// 追加機能：メニューバーへのボタン追加
// ===================================

/**
 * スプレッドシートを開いた時に実行される関数
 * メニューバーに「カスタム検索」という項目を追加します
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('カスタム検索')           // メニューバーに表示される名前
    .addItem('上位10サイト取得', 'mainProcess') // リストの名前と、実行する関数名
    .addToUi();
}

// ===================================
// 以下、ご提示いただいた既存コード（変更なし）
// ===================================
// 事前準備：以下の設定をご自身の環境に合わせてください
// ===================================

/**
 * Google Custom Search APIキー
 * @see https://console.cloud.google.com/apis/credentials
 * !!! 警告 !!!
 * 以前のキー（AIzaSyC...）は公開されているため、必ずGCPで再発行した
 * 新しいAPIキーを以下に貼り付けてください。
 */
const API_KEY = 'AIzaSyC8q9-2xlvcpPZn8lAlvZnO0FWYwERR0mM'; // ★★★ 必ず新しいキーに差し替える ★★★

/**
 * カスタム検索エンジン ID (CX)
 * (以前の会話でご提示いただいたご自身のIDを設定しています)
 */
const CX_ID = '33dbc55c71eb641c5';

/**
 * 検索キーワードが入力されているシート名とセル番地
 */
const KEYWORD_SHEET_NAME = 'Sheet1'; // （例: 'Sheet1'）
const KEYWORD_CELL = 'A1'; // （例: 'A1'）

/**
 * 結果を出力するシート名
 */
const RESULT_SHEET_NAME = 'Results'; // （例: 'Results'）

/**
 * 検索結果の取得件数
 */
const NUM_RESULTS = 10;

// ===================================
// メイン処理 (以前のコードと新しいロジックを統合)
// ===================================

/**
 * メイン関数：スプレッドシートからキーワードを取得し、検索と本文抽出を実行
 */
function mainProcess() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const keywordSheet = ss.getSheetByName(KEYWORD_SHEET_NAME);
  const resultSheet = ss.getSheetByName(RESULT_SHEET_NAME);

  if (!keywordSheet || !resultSheet) {
    SpreadsheetApp.getUi().alert('シートが見つかりません。シート名（' + KEYWORD_SHEET_NAME + ', ' + RESULT_SHEET_NAME + '）を確認してください。');
    return;
  }

  // キーワード取得
  const keyword = keywordSheet.getRange(KEYWORD_CELL).getValue();
  if (!keyword) {
    SpreadsheetApp.getUi().alert('キーワードが入力されていません（' + KEYWORD_SHEET_NAME + 'シートの' + KEYWORD_CELL + 'セル）。');
    return;
  }

  // 結果シートをクリア
  resultSheet.clear();
  // ★統合：スニペット列を追加し、ヘッダーを分かりやすく変更
  resultSheet.appendRow(['順位', 'サイト名', '記事タイトル', 'URL', 'スニペット', '本文(H2-4,P,Li,Blockquote,最大5万文字)']);

  try {
    // 1. 上位10サイトの取得 (以前の関数を流用)
    const searchResults = getTop10Sites(keyword);

    if (searchResults.length === 0) {
      resultSheet.appendRow(['検索結果がありませんでした。']);
      return;
    }

    // 2. 各サイトの本文を抽出
    searchResults.forEach((item, index) => {
      let extractedContent = '';

      // ★ベースコードの関数を利用
      const siteName = extractSiteName(item.site_name); // item.displayLink から item.site_name に変更

      try {
        // ★ベースコードの関数を利用 (fetchArticleFullText)
        extractedContent = fetchArticleFullText(item.url);
      } catch (e) {
        Logger.log(`本文抽出エラー (URL: ${item.url}): ${e.message}`);
        extractedContent = `本文の抽出に失敗しました: ${e.message}`;
      }

      // スプレッドシートに書き込み (★統合：スニペット(item.snippet)を追加)
      resultSheet.appendRow([
        index + 1,
        siteName,
        item.title,
        item.url,
        item.snippet, // スニペットを追加
        extractedContent
      ]);

      // ★統合：APIの連続実行を避けるため待機
      Utilities.sleep(500);
    });

    // ★統合：書式設定（折り返し表示）
    // B列 (サイト名), C列 (記事タイトル), D列 (URL), E列 (スニペット), F列 (本文)
    resultSheet.getRange('B2:F' + resultSheet.getLastRow())
      .setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);

    // 列幅を自動調整（本文(F列)以外）
    resultSheet.autoResizeColumn(2); // B列
    resultSheet.autoResizeColumn(3); // C列
    resultSheet.autoResizeColumn(4); // D列
    resultSheet.autoResizeColumn(5); // E列

    SpreadsheetApp.getUi().alert('処理が完了しました。');

  } catch (e) {
    Logger.log(`エラー発生: ${e.message}`);
    SpreadsheetApp.getUi().alert(`エラーが発生しました: ${e.message}`);
  }
}

// ===================================
// サブ関数群
// ===================================

/**
 * Google Custom Search API を使って上位サイトを取得する
 * (以前のコードから流用・安定版)
 */
function getTop10Sites(keyword) {
  const baseUrl = 'https://www.googleapis.com/customsearch/v1';
  const params = {
    key: API_KEY,
    cx: CX_ID,
    q: keyword,
    lr: 'lang_ja', // 言語を日本語に指定
    gl: 'jp',     // 国を日本に指定
    num: NUM_RESULTS, // 定数を使用
  };

  const queryString = Object.keys(params).map(key => `${key}=${encodeURIComponent(params[key])}`).join('&');
  const url = `${baseUrl}?${queryString}`;

  const options = {
    method: 'get',
    contentType: 'application/json',
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch(url, options);
  const json = JSON.parse(response.getContentText());

  if (json.error) {
    throw new Error(`Custom Search APIエラー: ${json.error.message}`);
  }

  if (!json.items || json.items.length === 0) {
    return [];
  }

  // 必要な情報を整形して返す
  return json.items.map(item => ({
    title: item.title,
    url: item.link,
    snippet: item.snippet,
    site_name: item.displayLink, // extractSiteName で使うため
  }));
}

/**
 * サイト名を抽出する（ドメインから取得）
 * (ご提示いただいたベースコードの関数)
 */
function extractSiteName(displayLink) {
  if (!displayLink) return '(サイト名不明)';
  return displayLink.replace(/^www\./, '');
}

/**
 * 指定URLから本文全体を抽出（見出し・リスト・引用含む）
 * (ご提示いただいたベースコードの関数 ＋ ★強化：User-Agent追加)
 */
function fetchArticleFullText(url) {
  try {
    // ★強化：User-Agentを追加して、ボット対策サイトからの取得成功率を上げる
    const options = {
      muteHttpExceptions: true,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
      }
    };
    const html = UrlFetchApp.fetch(url, options).getContentText('UTF-8');

    // ★ベースコードの本文抽出ロジックを呼び出す
    return extractMainText(html);
  } catch (e) {
    Logger.log('本文取得エラー: ' + url + ' - ' + e);
    return '(取得エラー)';
  }
}

/**
 * 本文を抽出するメインロジック
 * (ご提示いただいたベースコードのロジック ＋ ★統合：5万文字制限)
 */
function extractMainText(html) {
  const cleaned = html
    // 不要スクリプト・スタイル除去
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    // 不要要素除去（ご要望通り footer や section は残す）
    .replace(/<(header|nav|aside|form|noscript)[^>]*>[\s\S]*?<\/\1>/gi, '')
    // 改行・タブ統一
    .replace(/\r?\n|\t/g, '');

  // 本文・見出し・リスト・引用を抽出（堅牢化）
  const matches = cleaned.match(/<(p|li|h2|h3|h4|blockquote)[^>]*>([\s\S]*?)<\/\1>/gis);
  if (!matches) return '(本文抽出不可)';

  // タグ除去＋整形
  const text = matches
    .map(tag =>
      tag
        .replace(/<[^>]+>/g, '') // すべてのHTMLタグ除去
        .replace(/\s+/g, ' ')    // 空白整形
        .trim()
    )
    .filter(Boolean) // 空の行を除外
    .join('\n\n'); // 各要素（段落や見出し）の間に2つの改行を入れる

  if (!text) return '(本文抽出不可)';

  // ★統合：最大5万文字に制限
  return text.substring(0, 50000);
}

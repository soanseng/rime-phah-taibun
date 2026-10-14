# 台語發音・語音合成：共台語文字唸出來

<p><a href="https://taigi.anatomind.com/convert/#tts">漢羅轉換・台語發音</a>頁會使共台語文字<strong>唸出來</strong>：貼漢羅、台羅（TL）、白話字（POJ）抑是數字調攏會使，台語語音合成照讀音一句一句抑是規篇唸予你聽。語音佇你的瀏覽器本機合成，免安裝、免註冊、免費。</p>

<h3>按怎用</h3>
<ol>
<li>開<a href="https://taigi.anatomind.com/convert/#tts">轉換頁</a>，貼文章（親像：<code>我是台灣人，我愛講台語。</code>、<code>guá sī tâi-uân-lâng</code>、<code>Góa sī Tâi-oân-lâng</code>）。</li>
<li>勾「🔊 唸予我聽」（<strong>預設關</strong>；毋勾就毋會下載任何模型）。</li>
<li>撳「▶ 唸全篇」；抑是撳轉換結果逐句右上角的細 ▶，干焦唸彼句（漢→羅的 TL／POJ 輸出、羅→漢的漢字輸出攏有；羅→漢唸的是你原本輸入的羅馬字）。唸中閣撳就停。</li>
<li>唸的時陣，轉換結果內底這馬唸到的詞會光起來。時間是推算的：照逐段短語實際的聲音長度，按字母數分予逐詞，逐段短語重新對齊，所以可能略仔早抑略仔慢。顯示的詞佮唸的詞對袂齊（親像詞典揣無的字）就光規句。</li>
<li>多音字讀毋著？佇轉換結果點彼个字換讀音，唸法會綴咧改。</li>
</ol>
<p>斷句照句尾標點（。？！；. ? ! ;）佮換行；逗號、頓號、冒號是句內的短停，毋算一句。文章長（超過 12 句）建議一句一句唸：「唸全篇」會一路合成落去，較食電腦。</p>

<h3>下載佮儲存</h3>
<ul>
<li>頭一擺撳唸會下載語音模型：預設<strong>細版約 30 MB</strong>，會使換做<strong>原版約 58 MB</strong>；閣有語音引擎（ONNX Runtime Web，對 jsDelivr 載）約 11 MB。</li>
<li>模型存佇你的瀏覽器（Cache Storage），後擺通常免閣下載。清除網站資料、抑是瀏覽器空間無夠回收快取，就愛重新下載。換模型會清掉另一版的快取，免得兩版加起來 88 MB 佔空間。</li>
<li>欲清掉：瀏覽器設定 → 清除這个網站（taigi.anatomind.com）的資料。</li>
</ul>

<h3>原理（技術）</h3>
<ul>
<li><strong>模型</strong>：Meta <a href="https://huggingface.co/facebook/mms-tts-nan" target="_blank" rel="noopener">MMS-TTS 台灣台語模型（白話字 POJ）</a>（VITS 神經網路語音合成，單一聲音）。</li>
<li><strong>執行</strong>：<a href="https://onnxruntime.ai/" target="_blank" rel="noopener">ONNX Runtime Web</a>（WebAssembly）佇瀏覽器本機合成（背景 worker，合成的時網頁袂頓），<strong>文字毋會傳去伺服器</strong>。</li>
<li><strong>文字前處理</strong>：模型認得的拼寫是白話字，所以文字先用本站的轉換核心（佮輸入法仝一套詞典）轉做白話字本調，閣照句讀切句，逐句合成、頭一句好就先放。</li>
<li><strong>模型縮細</strong>：權重改存細版 int8（約 30 MB）抑是原版 fp16（約 58 MB），載入了照 fp32 計算。初步客觀量測（MFCC＋DTW 距離，單擺比較）兩版佮原始 fp32 模型的差異小，音質猶未經聽感評估；切塊放佇網站（主機單檔上限 25 MiB）。</li>
</ul>

<h3>授權</h3>
<p>語音模型是 <a href="https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hant" target="_blank" rel="noopener">CC BY-NC 4.0</a>（<strong>非商業用途</strong>）；ONNX 轉換出自 <a href="https://huggingface.co/willwade/mms-tts-multilingual-models-onnx" target="_blank" rel="noopener">willwade/mms-tts-multilingual-models-onnx</a>。本工具非商業用途，僅作台語學習教育之用。</p>

<h3>限制</h3>
<ul>
<li>干焦一種聲；MMS 系列模型用聖經朗讀錄音訓練，口氣可能較像讀經（音質猶未系統評估）。</li>
<li>變調由模型家己處理，毋一定準。</li>
<li>白話字鼻化符號 ⁿ 模型無支援，會唸做無鼻化。</li>
<li>詞典揣無讀音的字會略過，閣列出來予你看。</li>
</ul>

# murimondoGenerator
This system allows you to generate Murimondo by giving keyword or three words in the question of a murimondo.

無理問答（「一枚でも煎（千）餅とは、これ如何に」「一個でも饅（万）頭と言うが如し」）を生成するシステムです。環境構築が面倒なので、プログラムと実行結果の入ったipynbファイル、それをPythonに直したコード、説明資料（実行結果等含む）、実行を高速化するためのデータファイルが入っています。Word2Vecのモデルは「日本語Wikipediaエンティティベクトル」を、MeCabはNeologd辞書を使っています。

「日本語Wikipediaエンティティベクトル」
http://www.cl.ecei.tohoku.ac.jp/~m-suzuki/jawiki_vector/

Neologd辞書
https://github.com/neologd/mecab-ipadic-neologd/

無理問答について：『無理問答から見る、人工知能と身体性』
https://www.jstage.jst.go.jp/article/pjsai/JSAI2019/0/JSAI2019_4M2J903/_article/-char/ja/

人工知能学会での発表資料
https://github.com/GoNishimura/images/blob/master/人工知能学会2019発表資料.pdf


環境
<ul>
  <li>macOS High Sierra 10.13.6</li>
  <li>Python 3.3.7</li>
</ul>

出力例
<img src="https://github.com/GoNishimura/images/blob/master/無理問答生成器のコピー-1.png">

説明資料
https://github.com/GoNishimura/images/blob/master/無理問答生成器.pdf


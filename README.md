# murimondoGenerator
This system allows you to generate Murimondo by giving keyword or three words in the question of a murimondo.

無理問答（「一枚でも煎（千）餅とは、これ如何に」「一個でも饅（万）頭と言うが如し」）を生成するシステムです。環境構築が面倒なので、プログラムと実行結果の入ったipynbファイル、それをPythonに直したコード、説明資料（実行結果等含む）、実行を高速化するためのデータファイルが入っています。Word2Vecのモデルは「日本語Wikipediaエンティティベクトル」を、MeCabはNeologd辞書を使っています。

「日本語Wikipediaエンティティベクトル」
http://www.cl.ecei.tohoku.ac.jp/~m-suzuki/jawiki_vector/

Neologd辞書
https://github.com/neologd/mecab-ipadic-neologd/


環境
<li>
<ul>macOS High Sierra 10.13.6</ul>
<ul>Python 3.3.7</ul>
</li>

出力例
<img src="https://github.com/GoNishimura/images/blob/master/無理問答生成器のコピー-1.png">

説明資料
https://github.com/GoNishimura/images/blob/master/無理問答生成器.pdf


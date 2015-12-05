#!/usr/bin/env perl
# Coding: UTF-8
# 極悪けいじばん (改造版)
# Original by [micmic](http://www.satani.org/paso/paso029.html) plus:
# + OOP
# + Captcha
# + スパムフィルタ (spam.txt 内のキーワードのある書き込みを落とす。)
# + CSS (bbsstl.css を編集。)
# 公開時に次の方法で CAPTCHA をオフにしています。
# =captcha
# ...
# =cut
# の2行に囲まれている箇所はコメントアウトされます。

use strict;
use warnings;
use utf8;

use CGI;
#use Unicode::Japanese;
use Encode;
use Encode::JP::H2Z;
use LWP::UserAgent;
use Socket;

$\ = "\n";
my $ENCODING = ":encoding(shift_jis)";
my $sjis = Encode::find_encoding("shift_jis");
binmode STDIN, "$ENCODING";
binmode STDOUT, "$ENCODING";

=captcha
## G社 CAPTCHA 関係の global 変数たち。
# PUBKEY(公開鍵)とPRIKEY(秘密鍵)を間違えないように!
my $G_CAPT_PUBKEY = ""; # Site key
my $G_CAPT_PRIKEY = ""; # Secret key * 秘密鍵 *
=cut

my $KENSU_DEFAULT = 15; # ページ当りの表示件数デフォルト

#
# 以上おまじない完了。
# いまから定義するメインクラス Keijiban は、全体の挙動の管理が役割。
#

my $q = CGI->new;
my $bbs = Keijiban->new();
$bbs->main();

### MAIN CLASS ======

package Keijiban;

sub new($);
sub main($);
sub check_query_params($);
sub check_reload($);
sub write_message($);
sub record_hostname($);
sub spam_filter($);
sub replace_spec_chars($$);
sub maime_init($);
sub update_page_settings($);
sub print_logs($);
sub hankaku2zenkaku($$);
sub kishu_izon($$);
sub print_html_header($);
sub print_html_footer($);
=captcha
sub print_html_captcha($);
sub check_captcha_response($);
=cut

sub new($) {
    ## いわゆるコンストラクタ。
    ## メソッドたちへの参照ができるようになる。
    my $class = shift;
    my $hash = {
        'z91kUN1f' => "",
        'axUT3013' => "",
        'offset' => 0,
        'last' => 0,
        'lastcurrent' => 0,
        'no_older' => 0,
        'no_newer' => 0,
        'reloaded' => 0,
    };

    bless $hash, $class;
}

sub main($) {
    ## いわゆるメインメソッド。
    my $self = shift;
    my $cqp;

    # 入力をチェックする。指定なければショートカットして表示へいくす。
    # タイトルおよび本文のテキストを受信した場合、書き込みを実施。
    my $hdr = $q->header(-type=>'text/html', -charset=>'shift_jis');
    chomp $hdr;
    print $hdr;
    $cqp = $self->check_query_params();
    $self->maime_init();

    $self->print_html_header();
    if($cqp) {
        $self->write_message();
    }
    $self->update_page_settings();

    # ログ表示を行う。
    $self->print_logs();
    #print "CQP $cqp"; #d
    $self->print_html_footer();

}

sub check_query_params($) {
    ## GET, POSTメソッド入力をチェックする。
    my $self = shift;

    my @names = $q->param;
    my @names_url = $q->url_param;
    
    if (!@names) { return 0 }
    
    foreach my $k (@names_url) {
        chomp $k;
        #print " GET_" .$k;#d
        my $value = $q->url_param($k);
        $self->{$k} = $value; # 自分のメンバ変数として代入していく
    }
    foreach my $k (@names) {
        chomp $k;
        #print " POST_" . $k;#d
        my $value = $q->param($k) ? $sjis->decode($q->param($k)) : "";
        $self->{$k} = $value; # 自分のメンバ変数として代入していく
    }

    if (!$self->{'z91kUN1f'} or !$self->{'axUT3013'}) { return 0 }

    if ($self->check_reload()) { print "<b>Reloaded! <a href=\"./bbsn.cgi\">Reset</a> and try again.</b>"; return 0 }

    return 1;
}

sub check_reload($) {
    ## リロード対策。
    ## GET/POST入力を一時保存して、照合。
    my $self = shift;
    my $ref = "";
    my $chk = "";
    my $fpath_chk = "chk";

    return 0 if $self->{'axUT3013'} eq "";

    open my $fhc0, "<$ENCODING", "./$fpath_chk" or die;
    while(<$fhc0>){
        chomp;
        $chk = $chk.$_; 
    }
    close $fhc0;

    $ref = $self->{'z91kUN1f'}.$self->{'axUT3013'};
    chop $ref;
    if($chk eq $ref){
        # リロード時
        #
        $self->{'z91kUN1f'} = "";
        $self->{'axUT3013'} = "";
        return 1;
    } else {
        # リロードしてない時
        #
        open my $cfh1, ">$ENCODING", "./$fpath_chk" or die;
        print $cfh1 $ref;
        close $cfh1;
        return 0;
    }
}

############################################################
#
# ここから下は投稿書き込み用のサブルーチン定義。
#
#

sub write_message($) {
    ## メッセージをファイルに残す。#つきは過去の遺物とデバッグ用。
    my $self = shift;
    my $date = localtime;
    my $z91kUN1f = $self->replace_spec_chars($self->{'z91kUN1f'});
    my $axUT3013 = $self->replace_spec_chars($self->{'axUT3013'});

    return if $self->spam_filter();
=captcha
    return if $self->check_captcha_response();
=cut
    return if $self->{'axUT3013'} eq "";
    $self->{'last'}++;
    $self->{'lastcurrent'}++;
    my $log = sprintf("%04d.log", $self->{'last'});
    my $written_raw = <<END0;
<span style="font-size:smaller">おなまえ</span><br>
$z91kUN1f<br>
--------<br>
<span style="font-size:smaller">メッセージ</span><br>
$axUT3013
<br><span style="font-size:smaller">日付</span>
$date<br>
END0
    
    my $written = $written_raw;
    open my $fhl, ">$ENCODING", "./log/$log" or die "D $!$@";
    print $fhl $written;
    close $fhl;
    print "<b>書き込みました</b><br>"; #d
    $\ = "\n";
}

sub replace_spec_chars($$) {
    ## 制御文字を除去し、半角カナを全角へ。改行コードをUnix式(LFのみ)に統一。
    my $self = shift;
    my $tmp = shift;
    # 半角カナの処理。Unicode::Japanese又はEncodeの隠しコマンドを利用
    #$tmp = Encode::decode('utf8', Unicode::Japanese->new($tmp)->h2zKana->get);
    $tmp = $self->hankaku2zenkaku($tmp);

    $tmp =~ s/<!--[^<>]*-->//g;
    $tmp =~ s/\+/ /g;

    $tmp =~ s/\t//g;
    $tmp =~ s/\r\n/\n/g;    # Win (CRLF) to Unix (LF)
    $tmp =~ s/\r/\n/g;      # Mac (CR)   to Unix (LF)

    $tmp =~ s/&/&amp;/g;
    $tmp =~ s/\$/&#36;/g;
    $tmp =~ s/@/&#64;/g;
    $tmp =~ s/%/&#37;/g;
    $tmp =~ s/\\/&#92;/g;
    $tmp =~ s/"/&quot;/g; #"
    $tmp =~ s/'/&#39;/g; #'
    $tmp =~ s/</&lt;/g;
    $tmp =~ s/>/&gt;/g;
    # "'が無いと引用とかができない気もするがまあ何とか。

    return $tmp;
}

############################################################
#
# ここからはログ読み込みとHTML表示処理のためのものども。
#
#

sub maime_init($) {
    ## 最新ログナンバーをファイル一覧から取得。上位<kensu>件を表示する準備。
    my $self = shift;
    my @lognames;
    my @lognames_sort;
    my @dir;
    my $tmp;

    # ログのリスト取得
    opendir my $dirh, "./log/";
    @dir = readdir $dirh;
    closedir $dirh;
    @lognames = grep {/^[0-9]+.log/} @dir;
    @lognames_sort = @lognames ? sort @lognames : (0);

    # last := (int) 最新ログのファイル名 - 拡張子 -> 現在のログ数
    $tmp =  pop @lognames_sort;
    $tmp =~ s/^(....).*/$1/;
    $self->{'last'} = $tmp;
    $self->{'last'} += 0;
    
    # オフセットの適用 -> lastcurrent
    $self->{'offset'} += 0;
    if((!$self->{'offset'}) or ($self->{'offset'} < 0)) {
        $self->{'offset'} = 0;
    }
    $self->{'lastcurrent'} = $self->{'last'} - $self->{'offset'};

    # 1ページ当りの表示件数
    unless (defined $self->{'kensu'}) {
        $self->{'kensu'} = $KENSU_DEFAULT;
    }

}

sub update_page_settings($) {
    ## 保持している記事の件数の更新。読み込み時及び書き込みの後に実行される。
    my $self = shift;
    my $lastcurrent = $self->{'lastcurrent'};
    my $offset = $self->{'offset'};
    my $last = $self->{'last'};
    my $offset_older;
    my $offset_newer;
    my $maime;
    my $hyouji;
    my $pageme;
    

    # 最初のページ
    if($offset <= 0) {
        $self->{'no_newer'} = 1;
    }

    # offset_older ($self->{'kensu'}件新しい) の処理
    $offset_older = $offset + $self->{'kensu'}; # オフセット$self->{'kensu'}件分追加
    if($lastcurrent <= $self->{'kensu'}) { # 残りログ数が$self->{'kensu'}件未満のとき
        $self->{'no_older'} = 1;
    }

    # offset_newer ($self->{'kensu'}件分古い) の処理
    $offset_newer = $offset - $self->{'kensu'};
    if($offset_newer < 1) {
        $offset_newer = 0;
    }
    if($offset >= $last) {
        $self->{'no_older'} = 1;
        $offset_older = 0;
        $offset_newer = $last - $self->{'kensu'};
    }
    if($last <= $self->{'kensu'}) { # 全ログ数が$self->{'kensu'}件未満のとき
        $self->{'no_older'} = 1;
        $self->{'no_newer'} = 1;
        $offset = 0;
    }

    $self->{'offset_older'} = $offset_older;
    $self->{'offset_newer'} = $offset_newer;

    #print "Offsetは$self->{'offset'}です。"; #d
    if($lastcurrent <= 0 or $self->{'type'} eq 'all') {
        print "全 $last メッセージ。";
        if ($self->{'type'} eq 'all') {
            $self->{'no_older'} = 1;
            $self->{'no_newer'} = 1;
            $self->{'kensu'} = $last;
        }
        return;
    } 
    $last += 0;
    $self->{'offset'} += 0;
    $maime = int($offset / $self->{'kensu'} * 1.0) + 1;
    $hyouji = ($last + 0 < $self->{'kensu'}) ? "を" :
        $last - $self->{'offset'} >= $self->{'kensu'} ? "から $self->{'kensu'} 件ずつ" :
            "の最後の $lastcurrent 件を";
    $pageme = $last / $self->{'kensu'} > 1 ? "$maime ページ目です。" : "";
    print "全 $last メッセージ$hyouji 表示。$pageme";
}

sub print_logs($) {
    ## おのおのの書き込みファイルを読み込み表示する。
    my $self = shift;

    print "<!-- start showing posts -->\n<div id='posts'>\n";

    for (my $i = $self->{'lastcurrent'}; ($i > $self->{'lastcurrent'} - $self->{'kensu'}) and ($i > 0); $i--) {
        print "<!-- one post -->";
        print "<div class='ps'>\n";
        print "<h3 class=\'log_ban\' id=\'k$i\'>$i</h3>";

        # file name
        my $log = sprintf("log/%04d.log", $i);
        # open and print
        open my $fhl, "<$ENCODING", "./$log" or next;
        while(<$fhl>){
            print $self->kishu_izon($_);
        }
        close $fhl;

        print "</div>\n";
        print "<hr>\n";
    }

    print "</div>\n<!-- end showing posts -->\n";

}

sub hankaku2zenkaku($$) { 
    ## 半角カナを全角に。
    # From http://blog.livedoor.jp/dankogai/archives/51693618.html
    my $self = shift;
    my $eucjp = Encode::find_encoding('eucjp');
    my $str = $eucjp->encode(shift);
    Encode::JP::H2Z::h2z(\$str);
    return $eucjp->decode($str);
}

sub kishu_izon($$) {
    ## HTML表示前に改行をbrタグ、マル数字等を非機種依存の表現に置き換える。
    my $self = shift;
    my $tmp = shift if @_;

    $tmp =~ s/①/(1)/g;
    $tmp =~ s/②/(2)/g;
    $tmp =~ s/③/(3)/g;
    $tmp =~ s/④/(4)/g;
    $tmp =~ s/⑤/(5)/g;
    $tmp =~ s/⑥/(6)/g;
    $tmp =~ s/⑦/(7)/g;
    $tmp =~ s/⑧/(8)/g;
    $tmp =~ s/⑨/(9)/g;
    $tmp =~ s/⑩/(10)/g;
    $tmp =~ s/⑪/(11)/g;
    $tmp =~ s/⑫/(12)/g;
    $tmp =~ s/⑬/(13)/g;
    $tmp =~ s/⑭/(14)/g;
    $tmp =~ s/⑮/(15)/g;
    $tmp =~ s/⑯/(16)/g;
    $tmp =~ s/⑰/(17)/g;
    $tmp =~ s/⑱/(18)/g;
    $tmp =~ s/⑲/(19)/g;
    $tmp =~ s/⑳/(20)/g;
    $tmp =~ s/\n/<br>/g;

    return $tmp;
}

sub print_html_header($) {
    ## ヘッダーの表示。
    my $self = shift;
    my $hidden_kensu = $self->{'kensu'} == $KENSU_DEFAULT ?
                            '' : '?kensu=' . $self->{'kensu'};
    my $hidden_typeall = $self->{'type'} eq "all" ?
                            '?type=all' : '';
    my $hidden = $hidden_kensu ? $hidden_kensu : $hidden_typeall;
    print <<END1a;
<!DOCTYPE html>
<html lang="ja">
<head>
   <meta charset="shift_jis">
   <link href="./bbsstl.css" type="text/css"  rel="stylesheet">
   <title>はげましのお声、ないしは罵詈雑言 @ atablo.jp</title>
   <script src="https://www.google.com/recaptcha/api.js" async defer></script>
</head>
<body>
<h1>はげましのお声、ないしは罵詈雑言</h1>

<div class="form">
<form action="bbsn.cgi$hidden" method="post"> 
<p>御芳名</p>
<input name="z91kUN1f" type="text" value="匿名希望之介" tabindex="1"><br>
<p>おことば</p>
<textarea rows="10" cols="76" name="axUT3013" tabindex="2"></textarea>
END1a
=captcha
    $self->print_html_captcha();
=cut
    print <<END1b;
<p>準備はいいですね</p>
<input type="submit" value="書き込み" tabindex="3">
</form><a href="./bbsn.cgi">リセット</a>
</div>
<hr>
END1b
}

sub print_html_footer($) {
    ## フッターの表示。
    my $self = shift;
    my $ken = $self->{'kensu'} == $KENSU_DEFAULT ? "" : "&kensu=".$self->{'kensu'};
    my $kenolder = ($self->{'lastcurrent'} >= 2 * $self->{'kensu'}) ? $self->{'kensu'} : ($self->{'lastcurrent'} - $self->{'kensu'});
    my $kennewer = ($self->{'offset'} >= $self->{'kensu'}) ? $self->{'kensu'} : $self->{'offset'};
    my $link_older = $self->{'no_older'} ?
        "" : "    <a href=\"bbsn.cgi?offset=$self->{'offset_older'}$ken\">より古い $kenolder メッセージを読む。</a>\n";
    my $link_newer = $self->{'no_newer'} ?
        "" : "    <br><a href=\"bbsn.cgi?offset=$self->{'offset_newer'}$ken\">より新しい $kennewer メッセージを読む。</a>\n";
    my $link_all = ($self->{'no_older'} and $self->{'no_newer'}) ?
        "" : "    <br><a href=\"./bbsn.cgi?type=all\">すべてのメッセージを読む。</a>\n";
    print <<END2;
<div class="center">
$link_older$link_newer$link_all    <br><a href="./bbsn.cgi">最初のページに戻る。</a>
    <br><a href="../index.html">[Home]</a>
</div>
</body>
<!-- source code original copyrighted by www.satani.org-->
</html>
END2
}

sub record_hostname($) {
    my $self = shift;
    #my $host = $q->gethostbyaddr(inet_aton($ENV{REMOTE_ADDR}), $AF_INET); # use strict subs 環境下では使えないといわれる
    my $host = "$ENV{REMOTE_ADDR}";
    my $date = localtime;
    my $fpath_log = "spamhostlog.txt";
    my $line = "$date,$host";

    chomp $line;
    open my $fh0, ">>./$fpath_log";
    print $fh0 "$line";
    close $fh0;
}

############################################################
#
# これより下、スパムフィルタの実装と呼び出しメソッド。
#
#

sub spam_filter($) {
    ## 下記のスパムフィルタ関数達を呼び出し、いずれかが陽性なら1を返す。
    my $self = shift;
    my $axUT3013 = $self->{'axUT3013'};
    my $res = 0; # 無罪を推定

    # add some function code here

    # pattern match
    $res += $self->filter_ptnmatch($axUT3013);


    return $res;
}

sub filter_ptnmatch($$) {
    ## spam.txt に書かれた文字列とマッチしたら陽性。
    ## captcha で通っていてもダメ。
    my $self = shift;
    my $axUT3013 = shift;
    my $res = 0;
    my $fpath_spam = "spam.txt";

    open my $fh0, "<$ENCODING", "./$fpath_spam" or die "$!$@";
    while (my $line = <$fh0>) {
        chomp $line;
        if ($axUT3013 =~ /$line/) {
            print "<b class=\"errorwrite\">Spam word! $line</b><br>";
            $self->record_hostname(); # 不埒なホスト名を日付とともに記録
            $res = 1;
            last;
        }
    }
    close $fh0;
    return $res;
}

sub filter_naivebayes($$) {
    ## 学習済みのnaive Bayes言語モデルを用い、スパムであるという前提の
    # もっともらしさを求める。
    ## 0.5を上回れば陽性。 
    # TODO 
    my $self = shift;
}

sub naivebayes_learn($$) {
    ## スパムのチェックつき書き込みの内容から言語モデルを更新。
    # スパム書き込み達は同時に削除される。
    # TODO
}

############################################################
#
# Captcha 関係。
#
#
=captcha

sub print_html_captcha($) {
    ## CAPTCHA を表示。
    my $self = shift;
    print <<END3;
<div id="captcha">
  あなたはロボットではありませんか<br><small>(広告ブロックが入だと、表示されないかも)</small>
  <div class="g-recaptcha" data-sitekey="$G_CAPT_PUBKEY"></div>
</div>
<hr>
END3
}

sub check_captcha_response($) {
    ## G社 の CAPTCHA を提供するサーバにユーザの回答 (challenge request) を
    # POSTで送り、 まる付けの結果を得る。
    my $self = shift;
    my $ua = LWP::UserAgent->new();
    my $ua_res = $ua->post(
        "https://www.google.com/recaptcha/api/siteverify",
        {
            "response" => $self->{'g-recaptcha-response'},
            "secret" => $G_CAPT_PRIKEY
        },
        "User-Agent" => "Mozilla/1.0",
        "Content-Type" => "application/x-www-form-urlencoded"
    );
    my $result = $ua_res->content;
    #print "<i>GRCPT: $result</i><br>\n";#d
    if ($result =~ /"success": true/) {
        return 0;
    } elsif ($result =~ /"success": false/) {
        print "<b class=\"errorwrite\">Machigai! <a href=\"./bbsn.cgi\">Reset</a> and try again.</b><br>";
        return 1;
    } else {
        print "<b class=\"errorwrite\">Captcha error! <a href=\"./bbsn.cgi\">Reset</a> and try again, or contact the admin.</b><br>";
    }
    
}
=cut

1;
__END__

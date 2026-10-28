"""Prompt Sans: flattened ASCII outlines derived from DejaVu Sans.

Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: DejaVu fonts
Upstream-Author: Stepan Roh <src@users.sourceforge.net> (original author),
                  see /usr/share/doc/fonts-dejavu-core/AUTHORS for full list
Source: https://dejavu-fonts.github.io/

Files: *
Copyright: Copyright (c) 2003 by Bitstream, Inc. All Rights Reserved. 
 Bitstream Vera is a trademark of Bitstream, Inc.
 DejaVu changes are in public domain.
License: bitstream-vera
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of the fonts accompanying this license ("Fonts") and associated
 documentation files (the "Font Software"), to reproduce and distribute the
 Font Software, including without limitation the rights to use, copy, merge,
 publish, distribute, and/or sell copies of the Font Software, and to permit
 persons to whom the Font Software is furnished to do so, subject to the
 following conditions:
 .
 The above copyright and trademark notices and this permission notice shall
 be included in all copies of one or more of the Font Software typefaces.
 .
 The Font Software may be modified, altered, or added to, and in particular
 the designs of glyphs or characters in the Fonts may be modified and
 additional glyphs or characters may be added to the Fonts, only if the fonts
 are renamed to names not containing either the words "Bitstream" or the word
 "Vera".
 .
 This License becomes null and void to the extent applicable to Fonts or Font
 Software that has been modified and is distributed under the "Bitstream
 Vera" names.
 .
 The Font Software may be sold as part of a larger software package but no
 copy of one or more of the Font Software typefaces may be sold by itself.
 .
 THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF COPYRIGHT, PATENT,
 TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL BITSTREAM OR THE GNOME
 FOUNDATION BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, INCLUDING
 ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES,
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF
 THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM OTHER DEALINGS IN THE
 FONT SOFTWARE.
 .
 Except as contained in this notice, the names of Gnome, the Gnome
 Foundation, and Bitstream Inc., shall not be used in advertising or
 otherwise to promote the sale, use or other dealings in this Font Software
 without prior written authorization from the Gnome Foundation or Bitstream
 Inc., respectively. For further information, contact: fonts at gnome dot
 org.

"""
import base64
import json
import zlib
GLYPHS=json.loads(zlib.decompress(base64.b85decode(
    'c-rlK*{&_QvemDk`+@{>Ez-RWLWsWad+HvE|3LgZ9!=P}_NjA0;`P)+?VKy;%(TPdXh($q*I)eozxdm~rTV1LZ@>LEp68SDs(<+W'
    'R&)QfmiE;ejaU2fw>JAH)m8TOOf4=`nf3GFA`M?WWq!)U&C;8%a$dUG_dol;&tLoly}RMv^(mi`@I73m-uKnWBd&V?uK4r#ej48X'
    'l<%BBX*~NMd@kd=>@Sb@T^Bz0`90?+&Ak7?=QY0f*wV`TYnW6n-)nsGgMaY3j_=k!IgRg*@2~y){jrp9ylu_?y*{}mJv=?ner)~Z'
    'k-kUfA5#A=`wy#rr^!F$J)TX1H1+;XkoLX$r_}bX&ozHP>r+P60QMi+_ZXl0bd7NTVbAqb>+}7*?~n35+v^GK*;7uhSF}>UNwXM4'
    '>*>3{hq+hrJHIE=pQ)c{qCL;=Q4SS)?V^Hc)H~jLY1lW-+qyLFbB{aUHRx-<blx=@o96wshGV~c*1N_dr9BO;{wBcYiA?}7ANiu>'
    'VHTMKSL4ZXwI4tE;d}D)UY$HYb3Wg7@O2r~n6rLsH0e9-udl}(()R4q{yfD2bEfZBK5LJT9JVmp&q_-?uyWp{StW}!1%Lj4LL}^J'
    '6;oS%Q;2(LPp!|-+U!{P{n5#upg)&pVO0BbuBQCLsP`XgtjyZ$jz4UM;c~ClHg(ee3Hc-L@9q0t`s)d44~0A0uSg>n*JH@f^F7)f'
    'WXk#ZUh~c(Wz4SLX{OxzcS?r}2^--#G)j5DDdkJUJ*Gx7nZ~JXp4At$2&r(9&l>H|OJDFJ?q%0b^dj%i-Cw}`$rk34yhWMi(n#Z6'
    '?rpO-%l?!!lH54?3TDOU&BS|Wq&k)sG$%}~_N9sSs@qKy*$Y?n`?6wtK6*h~{s!K-2e$MAE)@6|GJ`^MQ|-I&UzA$3KxvQe8$$*)'
    'I=A!|etT^|QLj--U}w;HivzB6N_(Lb7UdaQrTv$_rR0ad=0fhjOft)6FAWBx+RU_nD#?(x<ia1Cr<3O5=j?Szkfiv-ll%ovZ*6Y$'
    '10WSXt65rMD*NM}qJLiS{I!LfZf`mJ^t~7N^hm5dzT7@@le<Wk?OojV7uqH>sr59l``lE{B5!&4g)OR@1nN`y2uR#y_QosHW@bsR'
    'jt6Yc<AUz#<n$SvF;{wt#xalZ+&gc72LEXQd*5u<9D5v|@t(}qPvl4~O`$;ET<2$|{ar}c{gSanv;lcK#DiQX+{aRK;qqSiw&m}B'
    '0wwC+iUUHw%}pK>3R@8(y$#9Ky`mUq+Y757>@B+=Ss~T*$hNn8`hamW2bKE+wX(_d=>7mBmrePa^#^c1_FLBzD+J^R9H<v&&=G$X'
    'L*|EK1e&y&LkqUfeqdUM3fRJ%-G>-oycRnLll$x+)fRN0Y11G$VXxRMpRMegWYWSiZ@Q2V7M`*nz9~qfWWTHIABzRX=JK_N@*V2o'
    '`G`FsBW!~FLz*Dvfe8Y!gK=`6yiQ$n+`={E;|!{8J7k+Nd-C4xpa(wZ_>3*gZ8~E^ZEk@m?9G4J3saM}w%O;=Gxt{1A0En}@>qgA'
    'Bk!e7uqmD#7Qn0$eoai9{FiMC^lCn*K;2&z!C=I6{9$vD6qy89**Bg}p$%rkABvc6woXabBs|8F=)(`1WOCy;Yn7(#^U)W!a9?;u'
    'FApD(s#I;GRfd^nsp_`5x`{S4hU!}SLa{wnJ6Q%|3vaA@r$KF`J+e%5pyKzNVq4w7=A2S1&*pX7u%%miS!-bS`wP(5+(xBr6Njcj'
    '*2jmo!IlY=U(XPqqiX4Vw{HnZO{^bxJiFg#w=LFlIq$C1lG0<_EGJVyV=oZv=}xWenNwzH=3u~f2?PDhfr)T=E3>D(2)m^zEol>e'
    'c-FBn5c26R+!l;v`LnP~TQSz%8Zy{o*n9}SSvD`sSk<~KIB#zN35wv&7K$s_cN<C4TW0Y6e`_smfEh~58)S9w5AC3wVgqT5Q9!-+'
    'V6MfVxkq!i^z|OjGd^pRm&ad+4f1?SJWcYz--Ie(vFX6J8Qfykl#A@(uKh$IvFX}!NCKGS9~chO-}?q!5lgf!9=AOJS10x~<iRIo'
    'K!<+%e5D{+fjRj3Iz-;1A7$SUqi?{#{Cs5zzEwB#?N7EiAU!t;zH-;k=jN2L_UEa`&kE-I%97Lrl-r-SHtXaj$oa25PV!z)59KTO'
    'YuoSHTx;j64r~z2pFEtn*M?lD((z4Lt&{{MiDM_%B*X05URd7rqyt%DG36C**S^^HQrR3;siQY1ZELCKVy9~}*tV7GveO8QYp-HE'
    'J{KhE-nm-^TBWzwHuv3GY@++uYk!IUgr5$>TZ&I_-%Hf}dJS*$t;gr_Z!xwcDK$Up=v?pYOOjV%+Tb5K#-!YKn2W@e=(=~@l!+s%'
    '@BKWz-}N{e1Np32YEUTUENE)`v0PCt_vXjPHt}Z3j{6n}3(qU~!;r*Sn*=4}4^0vU_F&>4k_|to@5+~UO=7cbr%B(QN5de+dci=m'
    '2D*7(Gn=6bH`Bqm-d6gfm6M&5ARb!@vqL7jxo+?OBnea>4<>_BkWriAv-fVd*`7pGZtej&x2?8(<p9irZ`%z22sT68U;6EjoKi(A'
    'dOdNA?MLkWny@5`GB#0$Z8~Ykfp-z7Xfn4}s+3tav*Cbm5w#aY#@Mqd50O`E?02vTA`!*b*0Z1y$}zOdzEM8#F-)edjWS|0{TTKg'
    'MpE5hl;HzE0t#wc%w}w3=(8FWf-PUR!VBY`#$ab4KnqHdyEoFjf_K1He;hyY6Xq5I+K7G!+z0Js4`Q>=@M?OT)amb;Y%O6?5|iD`'
    '5eqJA?B9;>H@WEI<`+R}r?qk@zV~{T<=_P&TgYYgioq-^^R=X~%SfPD^Rl<Q_8lWRzwe{=bRueF4{9#$S4vU%G7Yz<1s<*446e7t'
    'S_@_!SUkw|bgAjODJo)9fnzv(oDy8H4|<hFrxk7GEqC_Zwn~NlwRe~Hz?LjC+1^#i52|8Q7IdSXUiU`FP@WlEzwY^B>pwxMJ<J00'
    '9B!dliJP_1t<%P@v^fsv@cy>v_drKHV85j8`Og&Z*iVETPX~a*fO}J{O)<{>1;pLtCt@maAhu|cgOOoV?LCz(<u)~FEY5U&<qB$r'
    'rwMsZL7zMb$gj11#fO7j3sShYa8L&B<z|}-q7xjcmt)EIv$LGs4qf`kF3LZKxY=F-#LbIyHtpNb>yl6S^j=Plaew1|IT*fC%r&mk'
    '(0u!k%U=fbPcWFRpMM?9)7H=HKQR~ux7zFK27T|<FE9P46u6TDcZ>CH0!WqMvL{+9^L;g@xF`L%O!Rm5I?{zsCp24{VjZE5uur$W'
    'w(VE*1HvgV=Pd2Eo`(ybtco&?>=G=U7TsM0@?_pwiC;ywmui2K`G&D<gRCi{x+w=YcN<mv-4ajSR9|Uo2dx1<rvXP7a1}bsFyI(L'
    'n46ae?Kgd-uYc^f0so5z9G=x-R~8y@a@!Kjh|kv}TclN35wPJn?TYx%_%ugL>t@`|1k=V}fuNw+{BAPi7#AGPW?V<G1v@Os4x-Y{'
    '(`E#s@@W$V9)v8Z3JT*LAxRkehJO;47{b_)(IqUkz5Xq<`XAeIYuj<fZiRlmPMAhdU#mMxqqlFh62UPIFVQhdcl-%454wDwV1jSK'
    'SdiymQnMi^@)Wo_<&rPK`IE;h@?KlT<fk!5ihFq&!Q=vY{b<hReAk!u+&rs)&AG*RmCQLsa~ZFaIi~>dpbOW+dtiLJOxbf!7;kjq'
    'wwU!-#v@A%tmn8z{jRd+9FHs`tU1RHAI2vuV%ge5Tb3?NzlZ6L)JwKGm(RY7kn3^SCRJUt0f49#0@gJ>XKyDuQ)PwC4^R7;bNY-p'
    'Pl<02iiYkG3!aE&fIVVwZ_##PXs#>7)){@s+m8+hP%A@8A%o|UU7W}9`bMGkLa$R=xhj%<W26rQ#wi>_L?9`~^0+CXJ{0ZA$HyK`'
    ';U3zLV=-Ecn1s|3eiG3hnl}jIIM~x{^uK~V2%kb9;QMsz2Mr}fd#c#*`Q{k*YLidPa7e$2AGX|P$R32FB52rfv@V8ts3C@r?E~iO'
    '40<py5mqp4Q*dtT5hQsOt;a@B5mXro#$j_1ri*bO2L~AL+MB*5-$%@5(E`;25L;06STUVHj`%2WtDL5O-Jc>g?x(kiocQf^I$G`F'
    'kx}pP%NCC_-TC1yZJz1prG0DaAhMh4C0~XP=r8(0evQ`x3^RonX#1EgzZS4MzHnA}iC2RG#>wau21T9Nf-dPahDb-Gh+vWKU-RRb'
    'vPVzGaWCPZT#GRJR*bZ1M`SJcKwyl<%Fu#+7$#~F9v*P49xI3a7g$tCZahw;Y;!g-Ze;OaWn_($yx89@`=t|prc^?uO}AMxoSrQw'
    '9K{|sEfB#_@)0)3Kcfv&pI;0g8aVedOsq2AmnTnN){pBazHlyn&o2AL82aaXApNO-^*Da{&A<46`ORJmUTrP>DbAvlMNa?PF3k`p'
    'PktUl9%&g&F@Gi77~uSc_|&jNTbSIy1FU4=6*WYp_5#yorLzH>MFJU~*Ou5{1;Gy7&lP^l{zFYNf-<AH`w!S<l)#L*>_3dq3<UwW'
    'uY!1jGRs>*e7-8R8J@5=9zIT)T{MvP=cEnywONp#&h>U+ab3%~++Q8E!>037+!p(DlSJ4|T|l;QDh8d7{n<gnE%iI8BA+3_J_OlT'
    'I5s6=Uwt9%Ca;6(t8J{=sM*_j8@gZESW+?2sdxgkJ$C_!v7fMMAXPR8htMN~M#X~(No+8-j*Tg?j;wHkjiq2MMKL%ew!^=~b|{-7'
    'fAw~-6d2{j_vgB;{28H@yEj38c%dz@exIHH6`hcp{xAGIB5eG={N+*q8jl)%{PL(qH(Nj#WS>N$+>f)KS|2~IWlW6cUhFkgAROK%'
    'Q&3w>>#D2~w{iK)nEnk#P07Db??uI}kP!un%S+t!<N67A?1`6V1_gfSrT-Q$?TIg)5A#0^V70;k2@C|j4+(chH>&kJo%13Kfa<(I'
    'iy;$O090UG&tr^;+e+VOnBKCFhSC~|`8Bvwd`WGz7-4yn84!BKXC%laq-1m=sm@`-oP*a12a4uYL6~T6tA1JqSDNT++t)2yg~KZd'
    'gAB?SP?Eh7=lWd(;6cjAewKgTlSPuB-jM!Y_w6u&+Z`POwQb$uLztF%=f^0^ojw8+&!r9$x16iVmm^~k^j)4x(0|B~jP=<PgSTS='
    'BSLXj*cR@5Yyrvu#9PO`yOIDIC%(}ZV{Y+u=Hb(QJM}w!pBUX%-wg&xekD8-JexB=W{mIj6N97qQip-vEzb}6=q$`jUgogpCBG7j'
    '<u1>*!yBPXv3?0zptbG-6T|ZIA$|X_M?B&1PrTzWSPbHDphtOGH0E)+IHr0T-LyD6A&7OiO3?G}rbF_x;m)GOmW)+9dp4H!?CP`b'
    'vF{ICbO$jhB(`%Y5h+&`nFPwb)|CeUIG~2zM~@e<qzHX9g)+4Sh}x2~kUkslATUf4FKkx^qBLX1wnSHSJ`(X5FAP+e%XaD(buR-m'
    'jyh&)+XN*mo3b`Kg-<ULaTtV`07O;vhsj9Hf<dT2BmBVr0fI?ZC(}%qV|>5wkt*!qC$tfkuit?@h|qW%1%yG*uW=$irC)d|fKv&i'
    ';@QG+D(yv%lhX`(WgFKf>5M0u=&gi#&Q$^UBfnPdk#Vm@{Yp)=_o_1?m=1@WXwzoU?7IvvHAdR`Yk>gvZml0@>|0i@)@kle5!Fm<'
    '_)Giav^ih)24cKjwmTBG?SyOdCRV|N%*U{}HU&U3F3W!F_IAKO+AE#u_8KnrmN9KRYA2R~%;@BrIdXx`*Uzti2{iHU<p}-w#WH;O'
    '<te@U#dR9o<x3C#vaV-$x!aQu_7Bp;_Auq{4l-r$CNtshKJ>brjp}u~TiFYHH@hW+;!Lz9{v9LMrTtEVY$!ptMT@V*(gVqOJ{>IZ'
    '8N<2&%4y(pm&_c5p#i0(XvIT+b08EZJR#z491v9*RNwx*$vBr$e$QT@<$zdWg0~%n=R|A-B3;2&h}!&FTRJmJg?QP18nPEHa_Qp('
    '54Z+|82Mr3A%#?WDDIPCF-vI$!g^n~VWzkHbB29r_xkw>zV^!Z{QxC7UZ(*P0Z3?-XCUOmx>ICCY90cReV$7n;x}oGihf($Il5>1'
    'ZcQ>3-4Xpazj+6EeG<I2QO^491<w&4lJqU`xxDm$IvLi+3%lvCq5*h}ZsHHqkUc>EXr*IwR!1(F@9l=#0G$el`(S7hsKXx+i0%>J'
    'BxnULWyCiz+VCWqnq~lPi2&(AemHB!dPqtH)*`moY5)NRUs?ey*cy3pBljbCJ0qUZ^hOK9bp`{#^U@#Mn_=P$036uz*E3d)WS3uq'
    'NN;_Q1Tf0y4t1s+c7Z0t?e(7TsOK9b$S^)P2-cAt&X=UU7n_G9d9RLDc}V~$*M8NSbtr*#7q!QR^{RJ9jSjQ)M~-=A*7^B;pYY%R'
    '*?;-7|MF-5<<I`h|EvE3^!rB>DUBdF4Hzb_uIEB(l~0=#y)b5L=uyNZbLh!FzZo6u3YX2Elxpo4=7W#JY8F;^=4a#V8ZGN=Y$fmz'
    '42g<`_hwD{NKFU>bJiD14+e=)dtHi=32J=S%hST<#^<SsKhn+otidP68nZo>KW)dSU+nn$w&VK`GoE_y+VT0P9j_dVjaB<5*N$&*'
    'JKmnn%Z``p6NY?vGS`r|^F(9&I#<_{w*o$<yuqe_HsyaY<^Sy0|Gr<}P{q~(a}p*=g;ss<GJ*7v%iqEp0;t71f&YC%z5(Qvws_w{'
    'Qm-uVKt3oH5{M5#&n<3{R#Z_2G8sVixw-~;0%%Yabx42-2F&`A9tf^Ai8Hjk@4~T_71Dff=t4Z5)7St|rv4ctGSquiPX*$m8A}IR'
    '%4~<h^&eO{k(mKlsC%Jhw)SJUp|NdLA=WD8a-a74S0knrdP+{yV1B*#=0Z!A3=$F@f`4;hFQ<+YthuSpOn+283VrWjw}_3zZV!tV'
    '5e^!*V$iL%2xoKxatW`W14a()2GAxo40Fig@;RWp1dKbP1jT+uBBK7oe3F;P$&9Kn`$7~)fG5}?gXK5!=^&doD<Hj2r|$vQ_XEVA'
    'a}ONbGeWC1kgp*-#Lp<ngkg}xIdco`1$^8Tb57z=P!^!d4OX!=I1tm;x6{}%jal(QtAdIG;sMrs3TF?Xk4^e2E!MZ~0AoEnjgM8^'
    'dZtsT;4?DR`(wJsd->y>=I2j3fK!l=z0Hdp!0wX0t{mIkFB*0Lm$dXF(PM9B0p^P@Z1QB|TZACVf!uqj#|i&^T&F9!GlQSH@eVL)'
    'Tj23&i)5!b2}2;D0g~V#QDNk?6oDcDFs1;Mu7YY3f`A*jP^uTH2vjq@9l##m8_G#pB|6QjTgEJ?p%xVps5JY)DKq~~Z2DDB1qHO_'
    'XFc)#j5Pi>0^@mb58HJY1)rVyRBB~ZY8{F3XuxAer2|Wn6N5RDOAqTfKchM6xE8ThC_H&$MK<Mtn3Z*2s1ye(CRPAmAz6OE1X#&K'
    '29tEPh`Si5b|k}QnwE2KDj}q{;H`}_U>a=9raB*^j$jGxhtYuI_9<N0SqvUR{VIUWHEM)e&o{eJ>Jt(JMU7Eoo>(D+_))&$h=uAm'
    'rGROst$^-ARJOfXTOz6iU7!*|C?qSJoW`dZ0TvM@^T)XlR6~6|0R?vsQSlWlIU&N>V_;#T2BDA%(!H(SIiwu&)|1?ibnTXCKn>n5'
    'iMD^y<*S&6o7I-f#6{$-qLP@vtB_FrAVjs6iO{G1T1Q5eX1xo|J-Gfjss#1)ADN(jRM__r^>2Se!xw*cL6k9imm3x$G6?{Wx}_vA'
    'bRdQoqmQa;eyr1w)Gk|Bsq}OUCZMHJ$E!fyzJnQOBZld9;j;sgtq{Nh9GA)%Y1+e^dHe&2XuCJU6QGK_DK2F%xYCq^*+`;76By$y'
    's4?m&X;2yo-5ttncC)LIa!s@9kBYyG>z1HXfVL|RN44Uz&KfYKM!;SPc|R23Dz+sdgr8SABP{hMT)osoCu_nll{*0MxT@A%g>xf|'
    '^NM3=4pMB7vf5&P7(+ogbP1MK^oQ=6-2(Zih-z2RL}k$ie&8cW@IavH0djD$!&F!ZTnEeYvw^Nnp}r^E!bGu7=B`!w2<pAJhJj(D'
    'Yz0i}#$C=02cvI)^zNy9D%<8-0Dn#+!yw>`%_Rg@fS+%YFm=-6U#GA#kxjsEEWB*MR>9$N4yMV(1L}<;NE({lNMsm9KMjE`_xt{U'
    'qS0c16==C^bR0T8Y)M1wqFSy{?ndAhwQySxj8jaVD2WDq8f%ILT-bom8ra76L1@Pquf21&l^Ce8BmvM-Txf__g{DD;lS```HBB3*'
    'Jlj@xAk`88F)+2(3=a?+db^A*l4pc{Zrkh>>ams%E@pB0cE@V4N~?#0-VPRQ>nBIqJN(~(`LG=WDm<nGngqutMXy}m2O>d6hf<~Q'
    'KVR|IJ<sMi0;`|r$NGFFm0v|IQBTUxxs^f#6g&zc2Jl00<25;K{!|!o5J)h+EB#<SXGavsH~mqapfVo~C2@=h=<ZWhV_43{N5CLC'
    '_+9G>7>LDba{xi*dRVOdm*bQu>D)V3Q53{5QCMk2(i&_}(Zv&4ps(!7BjL9RV~jWOwtLr|&I$v{>I2s?*?T9T-zmTC)aY9Ya9UKv'
    '%R}F^N3B7C8BvFb9x>VFbGb7gla1|XHM1(WC@MCkk&Bro10)5Yxa304o8os^I;KR4kGK(O_E5ZI#Pane&0%;%f%L;#TS07Tf~yvn'
    'E7H_9qS&EqTf<VHG--9Mc7#ZQn<s|TW*qtzw0>R1f#t5ma4MwUi6l!cyoyDLXtxbF4G|rIC~m@?&q&Hm)`q&w764Pkb+TplV!;9X'
    '3-qXP*c=a98*qx6MI@+%SSMf`JJK1RrRwRZj~WbMlx~%=nE#5N9JsqwFRI-&h{}gwuHw5!H!m!K)d<P2q4q07JS}j}aP9U?nyHHJ'
    'ID2!p7QY69d~al{{LK~_jUDRkl|$FeVQ7?Mjzm{Xi4<0V$nE8tpm1dSUd8ag(HH~lXN{nb5Z)?Iq)gSYgf1^g;c)Lx7(hKNW+<3#'
    'x}XP-7>|z8meXCFRk{+c!Fe!Y3bMLc4ktj~+k8Trker90E?kB}wub87`o_uj4Dq$C^XA{8UUt75>PUVS$^*7;d{z|LJ`B~=aH?SY'
    'e9-43LUJ(No)o2!$Xq#I?I?=esby~ny92gw%@KAf3TIDy+uVLxv1*N|yDx$J-C%P=TovYBIi*5>vIKn~JlOl9n;xU8gjd3+DD+B?'
    'ROQgN;cIJQ9~70W4woH6G%(BQPBsWXv5F&FS)uWO$~s&K+ZL^!mYnDAs&|SYA7V2g9O^=tVn<ZJ>HBJ<vA3YU;3B&rzqF;uz-Zz4'
    '#ukN(e8l5^E(mb*8&A~1sXI=KI@j&t2^ZSjttFEW8C;Xm-Bd@+A`*Hkvj}QFPJIM&0P5M}o-wxNYrmCxgFI0Y>4-w(hps{R4gZPQ'
    'g+^@Y*M)oL8=26xirUzr>|Szn<$C`0t*@>tzTiJIZnhR36NOIQv*LZ(X19_k{nOy5^CJ?wpBg=&z#JL9Q5>oQz<JXh*=wm@6!JhT'
    'PT6TyP60eGic6^G?RezwAb2J89<n#GnkY_$fFolifdLpra)}bO3iN$)_lbvkpqzpwMxX7osdEcM=gWCKDy?oOPqA8y&w<`J<=#a~'
    'glp+vv#nRVPhUw&Dc%lec-*nADVHq9&Z5-K31@Qjs_)#l)JV{3hcugYsMZecwwJ)theKTQQhrf?+j?r*mQN%R8>HX$+kas3L#%IN'
    'ts48YIbA<5oHwT**R2~TK7n<|K9Q*mk+KGr+Nu!>?&$E76}F=zi<Uo6Js_t_!=^dzN8rN9)X~)$%ZGkX3lv0B>wz5Yo}i^6$|H)#'
    'Gz|<c?>lq>LFWd=;b6(Zu5(FJra@>8gzyQ?MQZ_SzQ$A<O&_sISgHua*L3fqbrP*h{~C>wV2t|VkT>_u$PNHUz1&2GdE^)~yvsf0'
    'm{M`4Ggs$2y%Y4vvda&_fVZhHio!*OU2;gi_3bte?wU;64tLQ|In-aPI>;9&C6y5QFR!kREwJ-PTIGDhsLz8WS~O>TcWit$a`aRG'
    '>wfCCdWqZWhxPI}Sa`fDOQNq^%98SxlUqIc8)>wQS6}UN^7cXvl8=UvPlBVbK+e)+>b8|Vs{f|B7FGYA*OuDfjowx<=RJ3l&mqG^'
    'r!E!b-ol%ld4U#!T}j5FTU~+ahNAARQ#p$N{?-eJcsZRp_RMs8bicgHqTK@jDDe3`U4c7%)BkwS_tj-H&-wGZ6jj*NsBhSN|9vSl'
    'H2z5~06n3W`0%5b9tF(!+RiS0U9>2yZAAc_7UK{w3ziCn7&0lafr|ZVRF5h)XTJ#nd#Xu<ajAy70yXGbAw5(Ss6<ea`^lY7Q0YS}'
    '6Ag_Fd`nh~iB9vut4!uXA*8!vK@>4W-x=Yu7+FD>jDZ^<oVKw^JKCWkNU-E6r9wj&Kf}8nCBg0f8aO4rUr%o(@HKipTw%Rk<Ew}Z'
    'ye3eF+q7wdh-NCb&FN=%KQVRKq9R}NWyVxq^hMaKzZRey$LIw@Y596BAT-^2FK}^^SoP}3@>Lxtd~;+Y==@u_9jLpEXAeSJ?yDz@'
    'xbDypQNmPW=*VaFcBh7hfOq1IV_mAC;}lRwK{TW__QMWQQQHd8QV@N$qJF4e6a?7-dWuCucg`{HqOSgi0Ql}<2><#pjGulO%5T3M'
    '=iyzR^!P8=YJQikHT%Q$CeGazrrzB*LEf{og8pak#R8q(87p|U?^$8*?^ypHITy+T;r!W}Rd4{VHcX<W3UnD|P?Aff-wOT@Hvt<C'
    '?JpGAG8PXUp~)(4bkBmdShtq2W!&bjR6$BpU@{wPmNQ;I0>%ip3xFiogeFC!Q#~+*qVjQ8QRm2xF_?>fN<BJ?ZDofTgvvsZoCBb;'
    'xKAbf55G_%x(zSe$WJ{0h_;AR@*V6?(q6+rkkLk>MhcJd0!%CVfdw$s^F>h6e-J^sTa}t%*=^HI(dkgDDPC=*dPTCsD_*fLZwasH'
    'SJYl=!3lFZtZ{;bXj60UAtng8RQwW+RB6WP!SFoT*C>L1px7A{;_Qe^d&mVK(|KovLh(Ca#{XaBP*0i{z0g#&zX;kDwmB3>wxzt5'
    'q!s}LV$Bf88LvexKafGXdpJTrz8s^6zj#V-f3cm0cRADJzs&0iUjFv{V*><v&JHp8?jACE?=Ca>?>_YM+@0$6yL(y7d-l4;!VBb|'
    'UiLz6VS}{!<ErrCndvg7EO=SNUp$u4HAlyJ02|f3E>+%9!z|3N_m_3bJs-ke&ZUZFpYyM8O?IHjk%B}h3Jwo8mTHa%05}-|LGl>!'
    'D<7bdq|Y<+K*~5#zc1|B67FS1V}i-%-CYGOzys7N4sK{qv8BXjCHm2gLCQ9**V^{G5ui)qIA`WZfrFJ}-IV)44Lc?FV2E@itCg;{'
    'rvqtX1$5rsxJFT<+u=^r&=3$8kM+SoK6krF=qagO5cL{!-r4Ef{q^B;eS8n8q2;}cCf`tth{922%~zXj_J7Xo!f@0-x-yI>)J5Wt'
    'kt`c8ME~g^#fH*=Nn7fmV<$gX6CNs*IyZ+(Rik592hG{owJI_=cpe*mlmOTa0&FPR^^GpX8yh0KWI{<tV_p%MU_X!&X&B@|pp04z'
    'K(fFf!;y_i_$D)-P3i7wEj}XPR@8znt2%r<A_G#Z%GL}<^h)%b=!}9WJxt$=kR7P~>iTqs6r}YP09NalQ`P`p)Dxm7M^ev?5`Cs?'
    'm=+O!1y9p~C`PryPUSp`yHg@~%uz&F^D@;bHjR_*ar87RJsXrUFdF_c4W7M<41Q+XcA{mAeTtlLca09)HZ1jXlir_9G^(FWb`%*U'
    'FdoDH81e{KDy36#;1o%T6CA|L9Kec=nCX?X-h|V6x+9YQePPpUwr_hPHOvrZOmFJ<PAJr*j5{!^YJ*Y~Za&R+@TSEUK8_1ifh}7A'
    '4VvT6klJ3??w&x-qP51*4x_#O6}3Cj;4%&QbjQNJvRgVjkulu91p()-o`!;5E$=aOqnYaN)1#vZ;hxPqWU*%`2yNJ!fh_fLUUO>M'
    '%ZQ$Y=xY<q=gxkrU{Jf9(;=K%b4CMpdzsm-{U`;B+xz$_Q*57Vw0{)J@g@lXXNAG~K;X6aZxGWGdKCzE?1U%UaGf^+zUa8bAie=z'
    'aYuR$4;id-&{X&XTAYtNp>-O{@0|z;|H)s&3>-M{AZm&pSpBN@u_>wE+%vCe7l@WZ6F3#+yBI1QW8K`^9L&-yt<TP80N*^$%snUt'
    '>QW4V2KA-m94O`xyU#rSVMZsRf#V`VaRBu?*zJ6s0~i+7oa(u77R3i<hxHH)4#e-G$28#E*{jf(n^c;59jKK;NTzh)!#0@9(O`mc'
    '3rjF$dOT`wHf`*%%ha}tOH|jaa+0$&Hp<J`*aJr&c`JvlEfA~D?!MN5hqDwW4hYp%S$Pv!=0w9qGp0%O(SQayY)&}b6LC{O|F<cy'
    'qBr5w)ImPbiTeUI#!u{%MSuq(nhrrT9@^GvmXinx1RS=-DFm%DYw2EUf}CJ?N9%r6C47)pafdrXB<lqgvSbW>wMq)i13Ji`eqf2g'
    'kc?bLioVW>63&=}jMLR))=hnCPgCQZorg2Nib~zUp~dE!y|~{w(#fZ{^5mfb$<6a8@1?*)u*d=ajlfW<d9daZFy_>2G(P7zKE*NT'
    'sjUo?xeFa3q`q(?h)Js$Y6%`;QBX@$K--WIw4I^nWN}h>ItyDkD>kII%hAZHP>y{0%oRlY(O$;}6bm=^a);k!fK=cYWGpT1&-~Er'
    '$l>-N?*1v>+=+cS!{=%JqrNwZ$+izfs+eP`OOg}1S>@@E5nEaPgq>~Ah7C;rHnUGAEpbjn?L&tLOIVqjJn0Z2bfbapPKuWi#t*zJ'
    '7a9RG_O^RW)9Svc-f2i|!AGvH6Q;^#Bj6}WOKQEElumC|_=;ptx2Z|66V=d>YBekc2LpUi>$)L+l9kd{6v-y)hoR23V=6&Aou~$k'
    '3IR9>b`>%6?4i_Mz?L9Hh;K>Gj{q>y!eU)4g+hUsHb*K-HB3uwItySM%OoKtdLWAAY?ig+{(Nn2+-=)&=_-$f9iM@K2si~YTT7=;'
    'M6+CAu9~AyK(hmP1Kn3`es6_?gtSyfX9~W@fip-G<Gdk5Ni(5zfOhIUphbPxd6bLO(1^ZF`2wTVAIA+1Vpz9+@|t&^E<iU)DuYbS'
    '($-VRgyV*eF@|ejsh3wHx|jAfi<a==Td{w632;Z$>|l)(T^>Hls1b)Zr@@+l^#Nk3upJcx$X7#B?Z*SZ-b4wWo)UBc*TRdk)@ke#'
    'EU1ekJbTD!4cwAz2-ui6S)$J+W=G|OyegtjbovWL{BqYeq&R0jVwL&JC+-(@#9RRgTuCR+$Snjqp$dzslD26Xo?IIy57MRS;T$Gc'
    '_y}d_Gd0lHZJ8ffoGt?o9xDTv$Rj5g2+(XyJ`oG4LY{SzEf7bx8CeWe>?{1Bq+k$|)bwGhCjwP!N9nm-@^YlyTp4&q_3dm1=DK19'
    'o8$3;8(iGx6N{?xa3~w^YT2k(paI^Z^=}X;zfs(&wYp7w(Q3e}T20_*byVwu!j#js4Pt$YGV02f<mwb3!jflEw*4{ghbK%VwWo9+'
    'jisZV+_lXO!Llt8)o@Uj@(h%$UY`1?ut{4OyF~{|u9A=&Bf6#PsEB&9EtI#@0<?6W&SXyscAXMq{(|#G%??CG%Q$zsx3AjWx!&O9'
    '^|-bDah#%YeYcJuO7KS8I#`hOdQw0n3sLMu&5(1R{=<*bi6d~MBmt5!Geukw7@9}59?$_wT*hf+!ll48kMrvuAz4&QAS@F+L?V3|'
    'LV?0M=TjvWMbCK}FHRMJwWwMG#6f+^qw_6&5=ADWR;qbVMzaHE_OtxwdaOC_{c&)#k4|eT<sN-Cm+FN3sVkvVRZbC>`bfgb@n2@Q'
    '*qSjIHUVM(gQvz}7<+56W&1%DcfhAxI6#G`RJpB;ax;k)8A2J6yD7GxVuuLEefNO~vMpz`)5!$RzKwtf7j0#=7jYNK+1agp0$n-m'
    ';lz<s^djoZix`8VO7UGlK-{94SIE1J3;4hhjIT?57pD=uFN+#70RMBY;+gSpaVg*Px@y%K?)DDozR)Jj&cCmtpLc&>t|nuarg?u<'
    'q*>X8fb~el0S$Z{0$dQu0nSy2X*SBnfhANqh@#-5i#uUd<KvK0W0mG-xlKo7(|4lIl>qJh=$L%tIf4i(JUVQMW11}*EiZpuvCr|b'
    'yDt&FP<%Wm7vbY@$ppdwJXlYi39x<81J&hpG)P$EM0TNsSOEy-*=GB8v9}H_EVSc_v-aS-PeVi&gH1CISc9v`LuXE7)yk6d0i0kx'
    'UFmT?SsW&Zz{R$%=4oE^Fjxe0Yu-jCsGVGKAYEqt1Drz_Nz)LiW8GqYrnTePhNROH3Qxp|txw2&iBm0=;qCRDSI|_sx>U17&>p)#'
    'j8g(C2z`l0IitE2WpkFbp`uKVJ?svg2N1<a=sWu%7S;zGZINO>46w#3$4cdjW2u+AvBW*O*Ls(E(SByXbhyDOvS)SgJT?1h{rjZb'
    '0HC^emSZVA<w<CK-F~Lf`F4h&jx&>K(tof@h~<}hY^>Lxp*<hEfb}R>*gW!k>;c*VD{^BDA!gobeFDO@U%BofL}-WcDW}&coOP#7'
    '@Dm)qs3xH-9|MT)>28dU^#0?XqKKFRFld}8EICBZqIpbS@{>^eA-un!tixVdk^ktHr-enW^r{p+T>{uQqa+efCxr_rH@m7^lFOCg'
    '0Tw!dx{D%CxpV^1>r};PG23)vNBDp2JoeFnKeP$u9d^5a?h(`ka`uUoVf`R-<$fY^4m&mb%5fl!4tz;&;RGZ1;gLs=`IjXLMkyj;'
    'f|7(8So_J61m>ldd%Qyd1au#u^Q{?%QRIvE--l;pbSpF*kW`%pV~Fo;Z{KAGaNb`7(eBfu@Ni@n)K)_8KGnh=Td&cULStv?cfE51'
    'xm0AtnGc`0Wx60tW6UuR2I(zQB%~^GDXNDf(eWcCNVFt~blwG<aq5QG6MZn+UG3>8M$1gl0$U-A9&n7pZ_6A<{jnsk0NM8ae0WN&'
    'w8kgoIB#dwkUmx+?Bh^AI{fzJM8;Yt(18Nj<)UDC2`sUlw|jCg#MjG^S7VeBX82@f`sjg2?+PgP=fcsE8f*d27tQPGa^2q`FrL{n'
    'uA*bEPxT`_*A*+~`Vu}Cb+oQO;i%?w>Qg3CVk7#LSy+z95L9Yzo~=0p;Pe^g8uN%sN9DBI{eOCdPgt+jm>z8{niHv1LL|dhQ($?9'
    'w=_No>4}0UYTi~?a`dIJJSFyk?=ll}e@vWpzRxaD@%6sD6stFnO{;Xro-df6b3?XDEq*z3oD<eASx|?hl)T8s12)$sD?lmjMfMc='
    'DK86zUV1HCDsJB4Wkm-TCzAUM`UQfk&RusAre<wJG!KbW9BOD+RoBPcXPjf_(IFL#^j3_1BDr4g>=-gQb4PXoVXdGHYx(D;9L%Hj'
    'qAWZ6=Sz81%FTRNX2}CQD~C#<&EK)GYrI$8HxEzv$A@S9@L(yw`*57cb~w^wKOF119gfz_gWpY;*bFAy*()aN*-Iw-*=t^wvlqQ='
    'XRmr$?_M6aCP!_N*ss4kG(YI$N9tj@4tlu0VyX|?I^E)6#u<=iqZ3zI$!!s5+B1bOCIpzkoF%&>6ae9~y}~xjJq1e?i&Q6`qnKn?'
    'pL!bQCcQa|69p-?JAc@s5#12zG4#u1GkC{sk}Iqpcm5ke*Bkgj%K}wo549@5>1Qh`ltkU!iw=$Du(>@~abG$2r$CvW=;wY3=-@+l'
    'dl-EHcuw)zB0Vy|_#9D67{v&)fpM3uAW%0&!xTejpFpM*ojyrNTcH)MDx!r4xr)$Z>?2H{Eh0)FT`PUs$lxz}A(0Qjkro7t*my6('
    'vcaL2Y)&k0oh42YB5VdBY>B_hqnQu~9r6L$Cu?P&k4UuAiGw0$gA>|uY*2)3@<;GDdU9+%gXn<cyG*B!7Ud~yON7D@3BSU?2Hiwi'
    'bvpljy7OqC^X2*t9~uPC8#Y&vyoK+_Ee-Tpr|&mi?uUuR*@OtB1Nc&+*Tc|fj46lHQ|bKa5Vr@V?DYOx6b%E68aX01joj}a(RG2R'
    'h;H_UP>JJZn3C>uoxV(jm!j^!MltiO6lzLHC!uiwA;@l-_0#(s>QV=oUOwf}JWASqQRD#Q07V~CrVc`<DN5GS(mBrOd{_*hBF0GQ'
    'EJ5$x6@rfo_MclF%~^+-*11tWd72fNJbJCT=R*5Lcep}N<SR~RnC_V76egfk?2y)dFdJp$sX0kS)zC&hO6y+a<C@Cnc}G_ELJZ&|'
    'SUp|fqujy+d}L427w}PM6$S8-qUHsB<WUbV;NxOy@B$x|th>NR9GLjVq9R|_U%<!8B-;f(`V_}#e8v57`(iOkd;4a|;=YZwX8X~3'
    '3)x0?20RVXid$qxKeQpibo-&D^zH!0!wP@&L(B5uPCv9gAoz#3AKIg1U~WIOPK3hkhlbqedUZ4FZkK!dosIqj90PabF?dG)*yG~M'
    '6d7mr+GE^UEr-kW30ghMp%o2h#JT#=T^^~G!l_&A_m==tP$VxkMYj#aD6HyJ@nrTPJUW@eXZj#S(%d{(X>oZ|?46WPC=|K}fr_%C'
    'krpALp?tQ+@83!EGa_X;3Vm=9<K-`;TQY>sLcd%q_U2Nh;@ISz=h#C2`V^zgUy4zNWO8D98+f>Lj(BB;Pi_bT+A3yFQl~jYp4+rG'
    'bwPFWEkGLByw+x2t?G&j70>U(7X9=R9ZDDrXLqb>^cL#HrqeWq-71Kza7_v`Ud`GH4eVf29z9AuTSFCM*KTWp2VPcJm^_TEJ@;;j'
    'u4ewV#K(DfiBOeajSi&kjtpf3x~-AtI40FIV^+VPd1q&kO%(v?R=ZS#GEh4&QI+Q$&P(+aJ)gWP&_A=>RZEf3_M*bi$iGv6($zI4'
    'O9u@!lv?_6jTD~(H|i(6TzG6B1n`%^u?YfF6f+ve`6A6ySe_#EC}XSyMmXnE1$Iz2K-q&FXd9R%2#w)kssLe94YsdblFHin!bqV@'
    'm}lam>8M%Y1GuItjbQvcR-8A}<p=(_UVg#D>t&~<s_<Yo3~ieyhZiyQy=I43-N5DWGCP1BP6t(9+W;pgqSrud6A%?Yj%|eO^?RFP'
    'P4<GGZ8%s$bGK<%y;AIAE%;z2l0Cla{_cv9URCn|dFqs$FnSa&RIZk;i{PV0#;1dyfIuK)-z>iJWOR}}&~<8KBhneNk<m;XiS}8}'
    '05Xk<);sf-aH0ihx32@gwPa$ICBKZ5e4-r-+RJ3M3bHyDvJyx_Md;D$2wC*UXY0wnx_PtF)DRq@Lxo>;N+NP^LP{<5Y(jdDGknyO'
    'iH8a*Ys;3shXr$OYF^&#DTUUBNYK%C50mWGRG>fIbS|Z$u1?z{TN4(&w1(|Ua4c1g5tL}3IhHe>(;0GB8n|x?uxZN>)iQrAHBjTK'
    '++O$59<1Hp&!>9N2b`h#*mL{SaYpj#>t8fQ&w%-v_Y|2teJ%~QW_*Ol4kA%AG9@2$WPL|jFH%Q2_+1RO_OExjR0-DK3yMaw5T<v{'
    '*?sbzOodT8-dqDyAAy<6SU}v(H|wQGhV*4lq+t7eu`jYi@U{B!<p-RPy8#X!wcn#a>$=;Aht(2~8qsBd5$D~1^u%8KlYai)zK~Jq'
    'NFCc7U?Ci%7uz4mdxUt~X`li@F`epV<2qnjT|v!b844qxiZW1eZfmx_+Pdxg0rBH>&<g(<Cx1pz4&X)Oz=zxEp+c8yOS#gc_q9sT'
    'fjqT)Q@B-H1nb#pq^l*2p3n%A0r<@Qq}q^oa8h)gK${vkH}!}-N<s}F3!_}6gv*82;+LV2@fdWv>gh;Dr)wUrRL3%KLL9g#40*72'
    '*BPNmu*}#G+ZlBeoyAxSB4WwS@V2#3q6KHNaS(wS`oZoloO!Ay4m%c(ybm80Xg!jsN4^5q@@x4Sk8(eETd6`}MtK4Naj&N%<+h0*'
    '2{y@`9_M$`7>+>$Qx40{Qv&VIbkQK9zKFr@Pvu3e#k1}YHHX?69cnk?O73!~FX&w_q+-TvL4~!A^{$V)#RfanDin0^OC!wrG8FTM'
    'hu;QUP+xvj-^IhQfb?t)cQ{(ff#7#kp|-mlvhp#pTe3o!v6~7{&pey0unOqxMIFI=wki&5Z+9oN{gU@N?192FPXzlMghLaSB4wn~'
    'IRMv`E&;UYLu7m!#&Jt2KaprHp|#}#sCDa#gh>T!Z>@h^0DAAs!WXHYrlX?;Go3^IR4uYlmytd=bfp}Y6e=(WwqSD|>mh37p%7ck'
    'ZoHNB8Fhcx6h>>PXxWCR#odt<TZ>;K(A(O5`cQ+k^LBLUspXDts@&uZo^>0q$wA)UsROPz$|Vd6t$M$NLkuskOW5T@91i92T$bp^'
    '+8{gw%i$~@!sM_uVs)1_UosZew;@II>-VUzH1bt%z{!?sw(K$FI6~QjWPg)q-dUs^dfd}Y`ScWS3b=;aDeiI^r~y-v2Sp3@Au<bN'
    'nC?2<o={#WhLVLF(Mq!QraCDbELoyE{g0yT!zlN@Iq5#ZtajgFUc93auijyrm+wT(?02f#3x^cmDwk9>+8_rpz1c3gV>_M&@qRrk'
    '790AkY3%q|^r8cd#1o7ZtRJYQ?S3U!nda02gI<V9mlM!6glM#esszL*mct;nf2VD>;)B|U<L`y%vlGgFeUKuILiPk6;?y4p--$zP'
    '5&j--loiru5SLk<X97w@6=s%J2v)ODD%$>4H9>OvmPL9(Ex3gD4O(~v!&D(=_nGz8=Ov&lhn*W7JRFbWRKv(vhW$`1;9wvc&dy3y'
    'x}e+7Qs;&e)jSMyx-Jh$xY|FgPPk>7I7D2@JM=316ch|C0}T+jt&zJc1Op<FYDb#+9i-nzoTNqXbvSxXv`RO66vrVU$`g@Cv=YNX'
    'e6`%fBD$8hKtt0#=#F+E(NSQ|WZ!NC-=b+o1di!gJMGA`GmeHuntrc$tI=<|v$YxuMuhvWY$c2|&l*1N2uA`YJ)B*Q(NWOFj6gA<'
    '71-lk4v<>=-H(9@>f+ekN)Cm6wSQFE<me}ec3=t+v%n5EYqmshxs?;XBEPiegey-YU+f*91=cBQ7H^<drfq@jfgDW+y%8u^Uz~?s'
    'oPc^&r)31GCrh7HIMUUK=`m$k4Udkq0Rt;aLp_h?%6O34x9GeZZnGy^wU*@LH>NA899+&}l~q;Y!vx}RXh!ppZ<%FN&O4;TYWAdw'
    'k9Lp><)ci7gB6Q|2kaB?+Rn#rFl?FW{xNieYYIuW6r}Aw1YSu^oj>7R7eqL!KdS_^v{yT@m67Z?52q#a_}R#BIgsr39ChmRY0vQp'
    'WP96lwDwDTj>jjaMR$(c-R~v3bD+Mu|LD%4##pyI2OO{UqdNy#=tp-BU|{Bt?i{)P+MNT8`Lj6(6WOok9F3mvZO+lwkLDbWIp5a_'
    'FO>n9*AXyGAivItp$qpuL<aSAZM;sI0pxh=gL@1OV*{@fIM+(AQ*7AWJ>N5Kz|R2Atf+8UY$59NabWYNdwR}*c1S*1rxOT!kKMsO'
    'T<spq)9O!jA|pjaCq~V|G&-?IiCR{IYn`+*9+m^cl-1E!$Cc%#pIhspeI<@RN``h6RnOT_gY&}HA5XNWU}E;G1<Ft5a*s7C`=Uk{'
    '->Di9qX)8)b=@I1MUDWoP?s|{b4}5w21i%$k=>qqH$DJo5CZ7h?a(2255y3%88bG@WaX+X<-xWtgH0*j;T8~#<Hf?qtUSdaM?DTj'
    'Thwa-+%bJ@1?=%WnK4)W7J4Bya;>7m4@J-HQ534?5a5(-qjuXbD-M>2t{j~(={65!??^)5Cbs|eb2{}Z?a|{IG|K(HpWDR>kppCv'
    '^qhAF1RbctNK<5EA_3j2n&Y{s)bwGcjtX%^K!QMA+*{RbKF3icS_0O%i21YI#n-O#ATJ^t+N&~0t4t%f)hiCeNN!6Ff6je0J<w4e'
    'egb=*yx)NkA|Dx}V6J<-#>pD?`I-sB3OuVU=8C2VFIoTrF~^HmuxLkqQL}U<9S^;W4qm$}0-K$kYGchXzBOK}iqJQ^&U@KQ`N0*w'
    'eVE3-KTPEp1kZT@hb2A2!?K>jVQJ6tu)IhR8^RQd-C_!!&14dv&E_>Yo6(DOHmg_hY-TU>-R$Io-j9RuH{l@c*YTX9${Hr4j1aF-'
    'AK~@BY|iH7*VV6u6uPthnAepafxGvLFXJ%2_Ao|K*VpHPIZDvUdR<jl;Sgh?U;W+J;4`}%J~7PK<xsgT#;~t=s47M#C<&)@FID(~'
    '`?%suzV}PIIvZx7i`6T(Jg+PDYhKZN=kxkSJ>P5Tb;Tl%EzhAvrcva+#80N*{kQO>#Zx-A9dmjqzPdOLXqJTm_=3Ot%fGxo#8+NF'
    '^tbW2^F!X|4}ZftME6~m5bMmz=f`DD+L}KuzmkwZ&(F)OmO`WJl5hFLeM{#FYkD*f($m*@oZ!9G^D0m%_tNi9?6r9>@i4yS?_3&y'
    'rU<2&`mam1Dj?1G6`AAzZ^{1pek(eNqwi8b9X4_49-Qlabt(Tp!OPE<L-E6|bdRh>;k$ZVa!v6C{`Bwhr+Z}V^%P@9f6ja5!oZKL'
    'fd*uf4)GvhH?CT1K6Rt+T^y~(;iv<<{@CpYj(5pPl%vjywjQ+v58LhcJ}v?ozYcIkWwVu=@T@dcsL?DBS(oDoauo`9MB~}25I(v_'
    'j3{0IjOC;WY9v|r6JEk2SzQcWg5`&(AmTnHx`8W5C`=+cj*#kIc0_1X1u}qdqt59l!T_Gf@qs=gy_vs59WVAgsS!X>q~s}n0wM}*'
    'g;w2OWC+Ic^z;Kki9FL#b*_SOs5-U*Os9{TG^)zsAXajQ9yDYKFhB8yW%y%`Fa~Rg5hx$wfg^ro-GuKio_{puXQDe6iy7C7Dxt*m'
    'W#(~YZlI`U6z)ut1e*bFNnh{@ABgdb!2uIy;c__c!_K8K4oy7~OB~J$Kc86C>^MIP<f~$J0(x_F!naCELOW)mSA`^PMYYiFbU2v)'
    'Lv!%?`EmRY4lU$6oAoH0rdJ)HD!xQig9ey^9#vr*LSSVltR-M>b;FY~q9ar!S`flXI{7G4_I4gmJA7h;Q}_c@$GScaGpIa*C#@;L'
    'UG2D!=`#f;8hoL?%#D_tx^o3`a@ce&c6E{}eX`4X6HkMa-->_;KvY>MZ}bjl=DU<=_CK5(Zwk-pq!89Yd-yO)rcR_=60UB$7v}+B'
    '&H0CEtawr6qPn|DQ35a_7AEg$c83XS2%E?GbwkjqfUL}qKdve0-KEWP{vrYIq!c3zO(-@oOZgF4K*neeH<6kyidTxzDIAzvQ$V^B'
    'XEdu@af>RbNsqrqIU~dy&*tkb&gU(R8-SWBm(*GG)yK-9%>l#-ME8hZaO8~<M}<5}%@KiJ+-E8d77J7ixd&`n?vWid&h?0DYaX53'
    'r$djB7k!-AVr9Rm6Pnav35iH%_s>9Adt_C8%$rZ02<Wd5=6dJ?Igf!y0AH`#?!+$ttb|nU!ox%eBP}izrIQRxIg%JzqPshUiL6wV'
    'MYBP~XH_?WLjIj+O1Wq3)UmNFJdLx)aA*`xC{eqT{LVt5CpHZQCMi(F^9cUbwW0&SrRfTIR&XuhIeT*k-tefdepVv@rRb^xy_k(C'
    '1sZ88f*5u^x_L<Q_spA*U|*;?gM*J&h1HSK%}ao6D_D|L5`+#!9NNQ(1R?v~XPu#>sJqv1e^}Oo5OSD#Q2$mMIHU!IZOs6T#&cWM'
    '*s8i+3>slkx5zl5c~Bzrf;xb~b2CZcrb5OZ^$*Bw<J8Tfy~ITKIpCD=Y@QP%7Z%403D~8xn2-n>>?NsY+)NE`L&uPLc&YGfyw>=<'
    'hu)&OBfDEPLcV)H-7eU|LWbDic-e5PmpDkTQ%!46p}0+<iHA8~`fO-)R(z$SEoy78E8X2{*T3k=52^WyC*z1bpWBzzqQgJNfvj<<'
    'g7`*Q@4eI)mIDf!%3li~<_~}P-~R^<_mQ3'
)))

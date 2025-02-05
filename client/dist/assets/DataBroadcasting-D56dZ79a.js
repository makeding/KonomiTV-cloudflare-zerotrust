import{d as c,m as g,M as E,U as A,u as v,_ as p,k as D,h as C,b as t,w as f,c as w,a as i,r as B,l as a,p as S,V,o as _,R as h}from"./index-B0k6gdhc.js";import{S as z}from"./Base-D8cEZLpl.js";import{V as b}from"./VSwitch-zNgBRYUt.js";import{b as y,c as $}from"./VTextField-BmhlGUcC.js";import{d as I}from"./VSelect-Btd_OyxJ.js";import"./Navigation-CdqQ4h9R.js";import"./ssrBoot-BOSN3Ea4.js";import"./VChip-BieH_rdX.js";import"./VAvatar-BpbVf3LE.js";const l="KonomiTV-BMLBrowser_nvram_prefix=receiverinfo%2F",k=c({name:"Settings-DataBroadcasting",components:{SettingsBase:z},data(){return{is_form_dense:A.isSmartphoneHorizontal(),data_broadcasting_zip_code:"",data_broadcasting_zip_code_validation:e=>e===""?!0:e.match(/^[0-9]{3}-[0-9]{4}$/)===null?"郵便番号は「000-0000」の形式で入力してください。":!0,data_broadcasting_prefecture:"255-0b0",data_broadcasting_prefectures:[{title:"未設定",value:"255-0b0"},{title:"西北海道",value:"2-0b000101101011"},{title:"東北海道",value:"1-0b000101101011"},{title:"青森県",value:"3-0b010001100111"},{title:"岩手県",value:"4-0b010111010100"},{title:"宮城県",value:"5-0b011101011000"},{title:"秋田県",value:"6-0b101011000110"},{title:"山形県",value:"7-0b111001001100"},{title:"福島県",value:"8-0b000110101110"},{title:"茨城県",value:"9-0b110001101001"},{title:"栃木県",value:"10-0b111000111000"},{title:"群馬県",value:"11-0b100110001011"},{title:"埼玉県",value:"12-0b011001001011"},{title:"千葉県",value:"13-0b000111000111"},{title:"東京都 (島部を除く)",value:"14-0b101010101100"},{title:"東京都島部 (伊豆・小笠原諸島)",value:"49-0b101010101100"},{title:"神奈川県",value:"15-0b010101101100"},{title:"新潟県",value:"16-0b010011001110"},{title:"富山県",value:"17-0b010100111001"},{title:"石川県",value:"18-0b011010100110"},{title:"福井県",value:"19-0b100100101101"},{title:"山梨県",value:"20-0b110101001010"},{title:"長野県",value:"21-0b100111010010"},{title:"岐阜県",value:"22-0b101001100101"},{title:"静岡県",value:"23-0b101001011010"},{title:"愛知県",value:"24-0b100101100110"},{title:"三重県",value:"25-0b001011011100"},{title:"滋賀県",value:"26-0b110011100100"},{title:"京都府",value:"27-0b010110011010"},{title:"大阪府",value:"28-0b110010110010"},{title:"兵庫県",value:"29-0b011001110100"},{title:"奈良県",value:"30-0b101010010011"},{title:"和歌山県",value:"31-0b001110010110"},{title:"鳥取県",value:"32-0b110100100011"},{title:"島根県",value:"33-0b001100011011"},{title:"岡山県",value:"34-0b001010110101"},{title:"広島県",value:"35-0b101100110001"},{title:"山口県",value:"36-0b101110011000"},{title:"徳島県",value:"37-0b111001100010"},{title:"香川県",value:"38-0b100110110100"},{title:"愛媛県",value:"39-0b000110011101"},{title:"高知県",value:"40-0b001011100011"},{title:"福岡県",value:"41-0b011000101101"},{title:"佐賀県",value:"42-0b100101011001"},{title:"長崎県",value:"43-0b101000101011"},{title:"熊本県",value:"44-0b100010100111"},{title:"大分県",value:"45-0b110010001101"},{title:"宮崎県",value:"46-0b110100011100"},{title:"鹿児島県 (南西諸島を除く)",value:"47-0b110101000101"},{title:"鹿児島県島部 (南西諸島の鹿児島県域)",value:"50-0b110101000101"},{title:"沖縄県",value:"48-0b001101110010"}]}},computed:{...g(v)},watch:{async data_broadcasting_zip_code(e){if(this.data_broadcasting_zip_code_validation(e)===!0)if(e!==""){const u=window.btoa(e.replace("-",""));localStorage.setItem(`${l}zipcode`,u)}else localStorage.removeItem(`${l}zipcode`)},data_broadcasting_prefecture(e){if(e!=="255-0b0"){const u=e.split("-0b"),o=parseInt(u[0]),r=window.btoa(String.fromCharCode(o));localStorage.setItem(`${l}prefecture`,r);const n=parseInt(u[1],2),d=window.btoa(String.fromCharCode(n>>8,n&255));localStorage.setItem(`${l}regioncode`,d)}else localStorage.removeItem(`${l}prefecture`),localStorage.removeItem(`${l}regioncode`)}},created(){const e=localStorage.getItem(`${l}zipcode`);if(e)try{this.data_broadcasting_zip_code=window.atob(e),this.data_broadcasting_zip_code=this.data_broadcasting_zip_code.slice(0,3)+"-"+this.data_broadcasting_zip_code.slice(3)}catch{}const u=localStorage.getItem(`${l}prefecture`);if(u)try{const o=window.atob(u).charCodeAt(0);for(const r of this.data_broadcasting_prefectures)if(r.value.startsWith(`${o}-`)){this.data_broadcasting_prefecture=r.value;break}}catch{}},methods:{resetNVRAMSettings(){for(const e in localStorage)e.startsWith("KonomiTV-BMLBrowser_nvram_")&&localStorage.removeItem(e);this.data_broadcasting_zip_code="",this.data_broadcasting_prefecture="255-0b0",E.success("データ放送の保存データをリセットしました。")}}}),M={class:"settings__heading"},R={class:"settings__content"},L={class:"settings__item settings__item--switch settings__item--sync-disabled"},N={class:"settings__item settings__item--switch settings__item--sync-disabled"},U={class:"settings__item settings__item--sync-disabled mt-2"};function T(e,u,o,r,n,d){const F=B("Icon"),m=B("SettingsBase");return _(),D(m,null,{default:C(()=>[t("h2",M,[f((_(),w("a",{class:"settings__back-button",onClick:u[0]||(u[0]=s=>e.$router.back())},[i(F,{icon:"fluent:chevron-left-12-filled",width:"27px"})])),[[h]]),u[7]||(u[7]=t("svg",{width:"27px",height:"27px",viewBox:"0 0 512 512"},[t("path",{fill:"currentColor",d:"M248.039 381.326L355.039 67.8258C367.539 28.3257 395.039 34.3258 406.539 34.3258C431.039 34.3258 453.376 61.3258 441.039 96.8258C362.639 322.426 343.539 375.326 340.539 384.826C338.486 391.326 342.039 391.326 345.539 391.326C377.039 391.326 386.539 418.326 386.539 435.326C386.539 458.826 371.539 477.326 350.039 477.326H214.539C179.039 477.326 85.8269 431.3 88.0387 335.826C91.0387 206.326 192.039 183.326 243.539 183.326H296.539L265.539 272.326H243.539C185.539 272.326 174.113 314.826 176.039 334.326C180.039 374.826 215.039 389.814 237.039 390.326C244.539 390.5 246.039 386.826 248.039 381.326Z"})],-1)),u[8]||(u[8]=t("span",{class:"ml-2"},"データ放送",-1))]),t("div",R,[t("div",L,[u[9]||(u[9]=t("label",{class:"settings__item-heading",for:"tv_show_data_broadcasting"},"テレビをみるときにデータ放送機能を利用する",-1)),u[10]||(u[10]=t("label",{class:"settings__item-label",for:"tv_show_data_broadcasting"},[a(" データ放送画面自体のオン/オフは、視聴画面右側のパネルからリモコンを表示した上で、リモコンの d ボタンから切り替えられます。"),t("br")],-1)),u[11]||(u[11]=t("label",{class:"settings__item-label",for:"tv_show_data_broadcasting"},[a(" データ放送機能をオンにすると、視聴時の負荷が若干高くなります。データ放送を利用しない場合や、スペックの低い Android デバイスで動作が重い場合は、オフに設定してみてください。"),t("br")],-1)),i(b,{class:"settings__item-switch",color:"primary",id:"tv_show_data_broadcasting","hide-details":"",modelValue:e.settingsStore.settings.tv_show_data_broadcasting,"onUpdate:modelValue":u[1]||(u[1]=s=>e.settingsStore.settings.tv_show_data_broadcasting=s)},null,8,["modelValue"])]),t("div",N,[u[12]||(u[12]=t("label",{class:"settings__item-heading",for:"enable_internet_access_from_data_broadcasting"},"データ放送からのインターネットアクセスを有効にする",-1)),u[13]||(u[13]=t("label",{class:"settings__item-label",for:"enable_internet_access_from_data_broadcasting"},[a(" この設定をオンにすると、データ放送機能を利用する際に、データ放送からインターネットにアクセスできるようになります。"),t("br"),a(" たとえば紅白歌合戦の視聴者投票をはじめとした双方向番組に参加したり、ネット接続時限定のミニゲームが遊べるようになります。"),t("br")],-1)),u[14]||(u[14]=t("label",{class:"settings__item-label",for:"enable_internet_access_from_data_broadcasting"},[a(" その一方で、"),t("b",null,"データ放送からのインターネットアクセスが有効な場合、あなたの視聴データがテレビ局に送信されることがあります。"),t("br"),a(" 大半のチャンネルでは個別に視聴データの送信を無効化できますが、依然プライバシー上の問題が残ります。 通常はオフにしておき、双方向コンテンツを使うときだけオンにすることをおすすめします。"),t("br")],-1)),i(b,{class:"settings__item-switch",color:"primary",id:"enable_internet_access_from_data_broadcasting","hide-details":"",modelValue:e.settingsStore.settings.enable_internet_access_from_data_broadcasting,"onUpdate:modelValue":u[2]||(u[2]=s=>e.settingsStore.settings.enable_internet_access_from_data_broadcasting=s)},null,8,["modelValue"])]),i(y,{class:"mt-6"}),t("div",{class:"settings__item settings__item--sync-disabled",onSubmit:u[4]||(u[4]=S(()=>{},["prevent"]))},[u[15]||(u[15]=t("label",{class:"settings__item-heading"},"お住まいの郵便番号",-1)),u[16]||(u[16]=t("label",{class:"settings__item-label"},[a(" ここで設定した郵便番号をもとに、データ放送の地域情報（ニュース・天気予報など）が表示されます。"),t("br"),a(" 設定しない場合、データ放送の一部のコンテンツが利用できないことがあります。"),t("br")],-1)),i($,{class:"settings__item-form",color:"primary",variant:"outlined",placeholder:"郵便番号",density:e.is_form_dense?"compact":"default",rules:[e.data_broadcasting_zip_code_validation],modelValue:e.data_broadcasting_zip_code,"onUpdate:modelValue":u[3]||(u[3]=s=>e.data_broadcasting_zip_code=s)},null,8,["density","rules","modelValue"])],32),t("div",U,[u[17]||(u[17]=t("label",{class:"settings__item-heading"},"お住まいの都道府県",-1)),u[18]||(u[18]=t("label",{class:"settings__item-label"},[a(" ここで設定した都道府県をもとに、データ放送の地域情報（ニュース・天気予報など）が表示されます。"),t("br"),a(" 設定しない場合、データ放送の一部のコンテンツが利用できないことがあります。"),t("br")],-1)),i(I,{class:"settings__item-form",color:"primary",variant:"outlined","hide-details":"",density:e.is_form_dense?"compact":"default",items:e.data_broadcasting_prefectures,modelValue:e.data_broadcasting_prefecture,"onUpdate:modelValue":u[5]||(u[5]=s=>e.data_broadcasting_prefecture=s)},null,8,["density","items","modelValue"])]),u[20]||(u[20]=t("div",{class:"settings__item"},[t("div",{class:"settings__item-heading text-error-lighten-1"},"データ放送の保存データをリセット"),t("div",{class:"settings__item-label"},[a(" このデバイス（ブラウザ）に保存されているデータ放送の保存データを、初期状態にリセット (消去) できます。"),t("br"),a(" 保存データには、データ放送内のミニゲームの得点、プレゼント企画のスタンプ個数、設定などが含まれます。"),t("br"),t("strong",{class:"text-error-lighten-1"},"保存データをリセットすると、元に戻すことはできません。十分ご注意ください。"),t("br")])],-1)),i(V,{class:"settings__save-button bg-error mt-5",variant:"flat",onClick:u[6]||(u[6]=s=>e.resetNVRAMSettings())},{default:C(()=>[i(F,{icon:"material-symbols:device-reset-rounded",class:"mr-2",height:"23px"}),u[19]||(u[19]=a("保存データをリセット "))]),_:1})])]),_:1})}const q=p(k,[["render",T]]);export{q as default};

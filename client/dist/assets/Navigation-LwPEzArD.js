import{d as P,r as I,u as R,a as T,o as L,w as z,c as b,b as f,e as B,f as g,g as k,h as d,i as u,j as o,v as H,x as q,s as G,y as U,X as F,V as w,k as C,R as m,_ as x,E as M,cW as j,G as K,cE as O,cM as X,cL as J,dM as Q,H as Y,dz as Z,cy as tt,I as et,dN as nt,c$ as at,cG as st,bR as S,cF as it,cP as ot,cR as rt,T as lt,dO as ut,cB as ct,cH as vt,L as dt,ct as _t,dP as ht,n as p,a8 as D,cj as ft,U as $,m as pt,z as gt,B as mt}from"./index-BhBe4R2M.js";import{_ as kt,V as A,u as yt}from"./ssrBoot-ii4gEpuF.js";function bt(t,e,n,c){function i(a){return a instanceof n?a:new n(function(r){r(a)})}return new(n||(n=Promise))(function(a,r){function v(_){try{s(c.next(_))}catch(l){r(l)}}function y(_){try{s(c.throw(_))}catch(l){r(l)}}function s(_){_.done?a(_.value):i(_.value).then(v,y)}s((c=c.apply(t,[])).next())})}function wt(t,e){var n={label:0,sent:function(){if(a[0]&1)throw a[1];return a[1]},trys:[],ops:[]},c,i,a,r;return r={next:v(0),throw:v(1),return:v(2)},typeof Symbol=="function"&&(r[Symbol.iterator]=function(){return this}),r;function v(s){return function(_){return y([s,_])}}function y(s){if(c)throw new TypeError("Generator is already executing.");for(;r&&(r=0,s[0]&&(n=0)),n;)try{if(c=1,i&&(a=s[0]&2?i.return:s[0]?i.throw||((a=i.return)&&a.call(i),0):i.next)&&!(a=a.call(i,s[1])).done)return a;switch(i=0,a&&(s=[s[0]&2,a.value]),s[0]){case 0:case 1:a=s;break;case 4:return n.label++,{value:s[1],done:!1};case 5:n.label++,i=s[1],s=[0];continue;case 7:s=n.ops.pop(),n.trys.pop();continue;default:if(a=n.trys,!(a=a.length>0&&a[a.length-1])&&(s[0]===6||s[0]===2)){n=0;continue}if(s[0]===3&&(!a||s[1]>a[0]&&s[1]<a[3])){n.label=s[1];break}if(s[0]===6&&n.label<a[1]){n.label=a[1],a=s;break}if(a&&n.label<a[2]){n.label=a[2],n.ops.push(s);break}a[2]&&n.ops.pop(),n.trys.pop();continue}s=e.call(t,n)}catch(_){s=[6,_],i=0}finally{c=a=0}if(s[0]&5)throw s[1];return{value:s[0]?s[1]:void 0,done:!0}}}var Ct=function(){function t(){var e=this;this.event=null,this.callbacks=[],this.install=function(){return bt(e,void 0,void 0,function(){var n=this;return wt(this,function(c){switch(c.label){case 0:return this.event?(this.event.prompt(),[4,this.event.userChoice.then(function(i){var a=i.outcome;return n.updateEvent(null),a==="accepted"})]):[3,2];case 1:return[2,c.sent()];case 2:throw new Error("Not allowed to prompt.")}})})},!(typeof window>"u")&&(window.addEventListener("beforeinstallprompt",function(n){n.preventDefault(),e.updateEvent(n)}),window.addEventListener("appinstalled",function(){e.updateEvent(null)}))}return t.prototype.getEvent=function(){return this.event},t.prototype.canInstall=function(){return this.event!==null},t.prototype.updateEvent=function(e){var n=this;e!==this.event&&(this.event=e,this.callbacks.forEach(function(c){return c(n.canInstall())}))},t.prototype.addListener=function(e){e(this.canInstall()),this.callbacks.push(e)},t.prototype.removeListener=function(e){this.callbacks=this.callbacks.filter(function(n){return e!==n})},t}(),N=new Ct;const St={class:"header"},Bt={key:0,class:"search-box"},Et=["placeholder"],$t=P({__name:"HeaderBar",setup(t){const e=I(!1),n=I(""),c=R(),i=T(),a=()=>{i.path.endsWith("/search")&&i.query.query&&(n.value=decodeURIComponent(i.query.query))};L(()=>{N.addListener(l=>{e.value=l}),a()}),z(()=>i.fullPath,a);const r=b(()=>i.path.startsWith("/videos")||i.path.startsWith("/mylist")||i.path.startsWith("/viewing-history")?"録画番組を検索...":"放送予定の番組を検索..."),v=()=>i.path.startsWith("/videos")||i.path.startsWith("/mylist")||i.path.startsWith("/viewing-history")?"/videos/search":"/tv/search",y=l=>{l.key==="Enter"&&!l.isComposing&&s()},s=()=>{if(n.value.trim()){const l=v();c.push(`${l}?query=${encodeURIComponent(n.value.trim())}`)}},_=b(()=>{const l=i.path;return!l.startsWith("/captures")&&!l.startsWith("/settings")&&!l.startsWith("/login")&&!l.startsWith("/register")});return(l,h)=>{const E=C("router-link"),V=C("Icon");return f(),B("header",St,[g((f(),k(E,{class:"konomitv-logo ml-3 ml-md-6",to:"/tv/"},{default:d(()=>h[2]||(h[2]=[u("img",{class:"konomitv-logo__image",src:kt,height:"21"},null,-1)])),_:1})),[[m]]),o(A),_.value?(f(),B("div",Bt,[g(u("input",{class:"search-input",type:"text",placeholder:r.value,"onUpdate:modelValue":h[0]||(h[0]=W=>n.value=W),onKeydown:y},null,40,Et),[[H,n.value]]),o(V,{class:"search-input__icon",icon:"fluent:search-20-filled",height:"24px",onClick:s})])):q("",!0),g(o(w,{variant:"flat",class:"pwa-install-button",onClick:h[1]||(h[1]=W=>F(N).install())},{default:d(()=>[o(V,{icon:"material-symbols:install-desktop-rounded",height:"20px",class:"mr-1"}),h[3]||(h[3]=U(" アプリとしてインストール "))]),_:1},512),[[G,e.value]]),h[4]||(h[4]=u("div",{class:"mr-3 mr-md-6"},null,-1))])}}}),Ut=x($t,[["__scopeId","data-v-89736472"]]),xt=M({baseColor:String,bgColor:String,color:String,grow:Boolean,mode:{type:String,validator:t=>!t||["horizontal","shift"].includes(t)},height:{type:[Number,String],default:56},active:{type:Boolean,default:!0},...j(),...K(),...O(),...X(),...J(),...Q({name:"bottom-navigation"}),...Y({tag:"header"}),...Z({selectedClass:"v-btn--selected"}),...tt()},"VBottomNavigation"),Vt=et()({name:"VBottomNavigation",props:xt(),emits:{"update:active":t=>!0,"update:modelValue":t=>!0},setup(t,e){let{slots:n}=e;const{themeClasses:c}=nt(),{borderClasses:i}=at(t),{backgroundColorClasses:a,backgroundColorStyles:r}=st(S(t,"bgColor")),{densityClasses:v}=it(t),{elevationClasses:y}=ot(t),{roundedClasses:s}=rt(t),{ssrBootStyles:_}=yt(),l=b(()=>Number(t.height)-(t.density==="comfortable"?8:0)-(t.density==="compact"?16:0)),h=lt(t,"active",t.active),{layoutItemStyles:E}=ut({id:t.name,order:b(()=>parseInt(t.order,10)),position:b(()=>"bottom"),layoutSize:b(()=>h.value?l.value:0),elementSize:l,active:h,absolute:S(t,"absolute")});return ct(t,ht),vt({VBtn:{baseColor:S(t,"baseColor"),color:S(t,"color"),density:S(t,"density"),stacked:b(()=>t.mode!=="horizontal"),variant:"text"}},{scoped:!0}),dt(()=>o(t.tag,{class:["v-bottom-navigation",{"v-bottom-navigation--active":h.value,"v-bottom-navigation--grow":t.grow,"v-bottom-navigation--shift":t.mode==="shift"},c.value,a.value,i.value,v.value,y.value,s.value,t.class],style:[r.value,E.value,{height:_t(l.value)},_.value,t.style]},{default:()=>[n.default&&o("div",{class:"v-bottom-navigation__content"},[n.default()])]})),{}}}),Wt={};function It(t,e){const n=C("Icon");return f(),k(Vt,{class:"bottom-navigation-container elevation-12",color:"primary",grow:"",active:""},{default:d(()=>[o(w,{class:p(["bottom-navigation-button",{"v-btn--active":t.$route.path.startsWith("/tv")}]),to:"/tv/"},{default:d(()=>[o(n,{icon:"fluent:tv-20-regular",width:"30px"}),e[0]||(e[0]=u("span",{class:"mt-1"},"テレビをみる",-1))]),_:1},8,["class"]),o(w,{class:p(["bottom-navigation-button",{"v-btn--active":t.$route.path.startsWith("/videos")}]),to:"/videos/"},{default:d(()=>[o(n,{icon:"fluent:movies-and-tv-20-regular",width:"30px"}),e[1]||(e[1]=u("span",{class:"mt-1"},"ビデオをみる",-1))]),_:1},8,["class"]),o(w,{class:p(["bottom-navigation-button",{"v-btn--active":t.$route.path.startsWith("/reserves")}]),to:"/reserves/"},{default:d(()=>[o(n,{icon:"fluent:timer-16-regular",width:"30px"}),e[2]||(e[2]=u("span",{class:"mt-1"},"録画予約",-1))]),_:1},8,["class"]),o(w,{class:p(["bottom-navigation-button",{"v-btn--active":t.$route.path.startsWith("/captures")}]),to:"/captures/"},{default:d(()=>[o(n,{icon:"fluent:image-multiple-24-regular",width:"30px"}),e[3]||(e[3]=u("span",{class:"mt-1"},"キャプチャ",-1))]),_:1},8,["class"]),o(w,{class:p(["bottom-navigation-button",{"v-btn--active":t.$route.path.startsWith("/mypage")}]),to:"/mypage/"},{default:d(()=>[o(n,{icon:"fluent:person-20-regular",width:"30px"}),e[4]||(e[4]=u("span",{class:"mt-1"},"マイページ",-1))]),_:1},8,["class"])]),_:1})}const Dt=x(Wt,[["render",It],["__scopeId","data-v-8139492e"]]);class Nt{static async fetchServerVersion(e=!1){const n=await D.get("/version");return n.type==="error"?(e===!1&&D.showGenericError(n,"バージョン情報を取得できませんでした。"),null):n.data}}const Pt=ft("version",{state:()=>({server_version_info:null,last_updated_at:0}),getters:{client_version(){return $.version},server_version(){var t;return((t=this.server_version_info)==null?void 0:t.version)??null},latest_version(){var t;return((t=this.server_version_info)==null?void 0:t.latest_version)??null},is_client_develop_version(){return this.client_version.includes("-dev")},is_server_develop_version(){var t;return((t=this.server_version)==null?void 0:t.includes("-dev"))??!1},is_update_available(){return this.server_version===null||this.latest_version===null?!1:this.is_server_develop_version===!1&&this.server_version!==this.latest_version||this.is_server_develop_version===!0&&this.server_version.replace("-dev","")===this.latest_version},is_version_mismatch(){return this.server_version===null?!1:this.client_version!==this.server_version}},actions:{async fetchServerVersion(t=!1){if(this.server_version_info!==null&&t===!1)return $.time()-this.last_updated_at>60&&this.fetchServerVersion(!0),this.server_version_info;const e=await Nt.fetchServerVersion();return e===null?null:(this.server_version_info=e,this.last_updated_at=$.time(),this.server_version_info)}}}),At=P({name:"Navigation",components:{BottomNavigation:Dt},computed:{...pt(Pt)},async created(){await this.versionStore.fetchServerVersion()}}),Rt={class:"navigation-container elevation-8"},Tt={class:"navigation"},Lt={class:"navigation-scroll"},zt={class:"navigation__link-text"};function Ht(t,e,n,c,i,a){const r=C("Icon"),v=C("router-link"),y=C("BottomNavigation"),s=mt("ftooltip");return f(),B("div",null,[u("div",Rt,[u("nav",Tt,[u("div",Lt,[g((f(),k(v,{class:p(["navigation__link",{"navigation__link--active":t.$route.path.startsWith("/tv")}]),"active-class":"navigation__link--active",to:"/tv/"},{default:d(()=>[o(r,{class:"navigation__link-icon",icon:"fluent:tv-20-regular",width:"26px"}),e[0]||(e[0]=u("span",{class:"navigation__link-text"},"テレビをみる",-1))]),_:1},8,["class"])),[[m]]),g((f(),k(v,{class:p(["navigation__link",{"navigation__link--active":t.$route.path.startsWith("/videos")}]),"active-class":"navigation__link--active",to:"/videos/"},{default:d(()=>[o(r,{class:"navigation__link-icon",icon:"fluent:movies-and-tv-20-regular",width:"26px"}),e[1]||(e[1]=u("span",{class:"navigation__link-text"},"ビデオをみる",-1))]),_:1},8,["class"])),[[m]]),g((f(),k(v,{class:p(["navigation__link",{"navigation__link--active":t.$route.path.startsWith("/timetable")}]),"active-class":"navigation__link--active",to:"/timetable/"},{default:d(()=>[o(r,{class:"navigation__link-icon",icon:"fluent:calendar-ltr-20-regular",width:"26px"}),e[2]||(e[2]=u("span",{class:"navigation__link-text"},"番組表",-1))]),_:1},8,["class"])),[[m]]),g((f(),k(v,{class:p(["navigation__link",{"navigation__link--active":t.$route.path.startsWith("/reserves")}]),"active-class":"navigation__link--active",to:"/reserves/"},{default:d(()=>[o(r,{class:"navigation__link-icon",icon:"fluent:timer-16-regular",width:"26px",style:{padding:"0.5px"}}),e[3]||(e[3]=u("span",{class:"navigation__link-text"},"録画予約",-1))]),_:1},8,["class"])),[[m]]),g((f(),k(v,{class:p(["navigation__link",{"navigation__link--active":t.$route.path.startsWith("/captures")}]),"active-class":"navigation__link--active",to:"/captures/"},{default:d(()=>[o(r,{class:"navigation__link-icon",icon:"fluent:image-multiple-24-regular",width:"26px"}),e[4]||(e[4]=u("span",{class:"navigation__link-text"},"キャプチャ",-1))]),_:1},8,["class"])),[[m]]),g((f(),k(v,{class:p(["navigation__link",{"navigation__link--active":t.$route.path.startsWith("/mylist")}]),"active-class":"navigation__link--active",to:"/mylist/"},{default:d(()=>[o(r,{class:"navigation__link-icon",icon:"ic:round-playlist-play",width:"26px"}),e[5]||(e[5]=u("span",{class:"navigation__link-text"},"マイリスト",-1))]),_:1},8,["class"])),[[m]]),g((f(),k(v,{class:p(["navigation__link",{"navigation__link--active":t.$route.path.startsWith("/viewing-history")}]),"active-class":"navigation__link--active",to:"/viewing-history/"},{default:d(()=>[o(r,{class:"navigation__link-icon",icon:"fluent:history-20-regular",width:"26px"}),e[6]||(e[6]=u("span",{class:"navigation__link-text"},"視聴履歴",-1))]),_:1},8,["class"])),[[m]]),o(A),g((f(),k(v,{class:p(["navigation__link",{"navigation__link--active":t.$route.path.startsWith("/settings")}]),"active-class":"navigation__link--active",to:"/settings/"},{default:d(()=>[o(r,{class:"navigation__link-icon",icon:"fluent:settings-20-regular",width:"26px"}),e[7]||(e[7]=u("span",{class:"navigation__link-text"},"設定",-1))]),_:1},8,["class"])),[[m]]),g((f(),B("a",{class:p(["navigation__link",{"navigation__link--develop-version":t.versionStore.is_client_develop_version,"navigation__link--highlight":t.versionStore.is_update_available}]),"active-class":"navigation__link--active",href:"https://github.com/tsukumijima/KonomiTV",target:"_blank"},[o(r,{class:"navigation__link-icon",icon:"fluent:info-16-regular",width:"26px"}),u("span",zt,"version "+gt(t.versionStore.client_version),1)],2)),[[m],[s,t.versionStore.is_update_available?`アップデートがあります (version ${t.versionStore.latest_version})`:"",void 0,{top:!0}]])])])]),o(y)])}const Ft=x(At,[["render",Ht],["__scopeId","data-v-0ca594b5"]]);export{Ut as H,Ft as N,Nt as V,Pt as u};

import{d as h,q as o,s as q,x as f,z as B,c as b,a as n,b as l,k as w,e as S,A as V,U as k,B as M,o as v,_ as R}from"./index-B7OgWKtM.js";import{B as U,R as N}from"./RecordedProgramList-c8g7Jb3l.js";import{H as x,N as C}from"./Navigation-CnqcZDIH.js";import{S as I}from"./SPHeaderBar-kw61mg0f.js";import{V as O}from"./Videos-d0PD3lY7.js";import"./VDialog-B5uyaSNw.js";import"./VChip-CXvR9eN_.js";import"./VTextField-Cn4WKwf3.js";import"./VAvatar-CxE9IZav.js";import"./VCard-CZrRuC1N.js";import"./ssrBoot-CgU2lsL7.js";import"./VSelect-9qvNrm53.js";const P={class:"route-container"},$={class:"videos-search-container-wrapper"},E={class:"videos-search-container"},H=h({__name:"Search",setup(L){const a=B(),i=M(),r=o(""),c=o([]),p=o(0),t=o(!0),s=o(1),u=o("desc"),d=async()=>{const e=await O.searchVideos(r.value,u.value,s.value);e&&(c.value=e.recorded_programs,p.value=e.total),t.value=!1},g=async e=>{s.value=e,t.value=!0,await i.replace({query:{...a.query,page:e.toString()}})},y=async e=>{u.value=e,s.value=1,t.value=!0,await i.replace({query:{...a.query,order:e,page:"1"}})};return q(()=>a.query,async e=>{e.query!==r.value&&(s.value=1),r.value=e.query,await d()},{deep:!0}),f(async()=>{r.value=a.query.query,a.query.page&&(s.value=parseInt(a.query.page)),a.query.order&&(u.value=a.query.order),await d()}),(e,m)=>(v(),b("div",P,[n(x),l("main",null,[n(C),l("div",$,[n(I),l("div",E,[n(U,{crumbs:[{name:"ホーム",path:"/"},{name:"ビデオをみる",path:"/videos/"},{name:"検索結果",path:`/videos/search?query=${encodeURIComponent(r.value)}`,disabled:!0}]},null,8,["crumbs"]),!t.value||c.value.length>0?(v(),w(N,{key:0,title:V(k).isSmartphoneVertical()?"検索結果":`「${r.value}」の検索結果`,programs:c.value,total:p.value,page:s.value,sortOrder:u.value,isLoading:t.value,showBackButton:!0,breadcrumbs:[{name:"ビデオをみる",path:"/videos/"},{name:"検索結果",path:`/videos/search?query=${encodeURIComponent(r.value)}`}],"onUpdate:page":g,"onUpdate:sortOrder":m[0]||(m[0]=_=>y(_)),emptyMessage:`「${r.value}」に一致する録画番組は見つかりませんでした。`,emptySubMessage:"別のキーワードで検索をお試しください。",showEmptyMessage:!t.value},null,8,["title","programs","total","page","sortOrder","isLoading","breadcrumbs","emptyMessage","showEmptyMessage"])):S("",!0)])])])]))}}),Z=R(H,[["__scopeId","data-v-a2a7c279"]]);export{Z as default};

import{d as q,u as w,q as i,s as v,x as B,z as M,c as S,a as l,b as _,B as b,o as R,_ as V}from"./index-lGC112h2.js";import{B as x,R as I}from"./RecordedProgramList-0YtUuT8R.js";import{H as N,N as O}from"./Navigation-kt4PSEFC.js";import{V as P}from"./Videos-DNFGQPHu.js";import"./VDialog-Bp2GBOY8.js";import"./VChip-BY9v4WK4.js";import"./VTextField-BvJ4Zmpe.js";import"./VAvatar-BsZhzxO7.js";import"./VCard-C5n1MbJM.js";import"./ssrBoot-fQehJ0Va.js";import"./VSelect-CB1P8YQI.js";const k={class:"route-container"},E={class:"mylist-container-wrapper"},L={class:"mylist-container"},H=q({__name:"Mylist",setup(U){const a=M(),g=b(),y=w(),n=i([]),u=i(0),r=i(!0),o=i(1),t=i("mylist_added_desc"),p=async()=>{const e=y.settings.mylist.filter(s=>s.type==="RecordedProgram").sort((s,m)=>{switch(t.value){case"mylist_added_desc":return m.created_at-s.created_at;case"mylist_added_asc":return s.created_at-m.created_at;case"recorded_desc":case"recorded_asc":return m.created_at-s.created_at;default:return 0}}).map(s=>s.id);if(e.length===0){n.value=[],u.value=0,r.value=!1;return}let c="ids";t.value==="recorded_desc"?c="desc":t.value==="recorded_asc"&&(c="asc");const d=await P.fetchVideos(c,o.value,e);d&&(n.value=d.recorded_programs,u.value=d.total),r.value=!1},f=async e=>{o.value=e,r.value=!0,await g.replace({query:{...a.query,page:e.toString()}})},h=async e=>{t.value=e,o.value=1,r.value=!0,await g.replace({query:{...a.query,order:e,page:"1"}})};return v(()=>a.query,async e=>{e.page&&(o.value=parseInt(e.page)),e.order&&(t.value=e.order),await p()},{deep:!0}),v(()=>y.settings.mylist,async()=>{await p()},{deep:!0}),B(async()=>{a.query.page&&(o.value=parseInt(a.query.page)),a.query.order&&(t.value=a.query.order),await p()}),(e,c)=>(R(),S("div",k,[l(N),_("main",null,[l(O),_("div",E,[_("div",L,[l(x,{crumbs:[{name:"ホーム",path:"/"},{name:"マイリスト",path:"/mylist/",disabled:!0}]}),l(I,{title:"マイリスト",programs:n.value,total:u.value,page:o.value,sortOrder:t.value,isLoading:r.value,showBackButton:!0,showEmptyMessage:!r.value,emptyIcon:"ic:round-playlist-play",emptyMessage:"あとで見たい番組を<br class='d-sm-none'>マイリストに保存できます。",emptySubMessage:"録画番組の右上にある ＋ ボタンから、<br class='d-sm-none'>番組をマイリストに追加できます。",forMylist:!0,"onUpdate:page":f,"onUpdate:sortOrder":c[0]||(c[0]=d=>h(d))},null,8,["programs","total","page","sortOrder","isLoading","showEmptyMessage"])])])])]))}}),X=V(H,[["__scopeId","data-v-343c315e"]]);export{X as default};

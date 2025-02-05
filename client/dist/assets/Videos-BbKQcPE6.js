import{aq as t,ag as s}from"./index-B0k6gdhc.js";const o={id:-1,status:"Recorded",file_path:"",file_hash:"",file_size:0,file_created_at:"2000-01-01T00:00:00+09:00",file_modified_at:"2000-01-01T00:00:00+09:00",recording_start_time:null,recording_end_time:null,duration:0,container_format:"MPEG-TS",video_codec:"MPEG-2",video_codec_profile:"High",video_scan_type:"Interlaced",video_frame_rate:29.97,video_resolution_width:1440,video_resolution_height:1080,primary_audio_codec:"AAC-LC",primary_audio_channel:"Stereo",primary_audio_sampling_rate:48e3,secondary_audio_codec:null,secondary_audio_channel:null,secondary_audio_sampling_rate:null,cm_sections:[],created_at:"2000-01-01T00:00:00+09:00",updated_at:"2000-01-01T00:00:00+09:00"},l={id:-1,recorded_video:o,recording_start_margin:0,recording_end_margin:0,is_partially_recorded:!1,channel:null,network_id:null,service_id:null,event_id:null,series_id:null,series_broadcast_period_id:null,title:"取得中…",series_title:null,episode_number:null,subtitle:null,description:"取得中…",detail:{},start_time:"2000-01-01T00:00:00+09:00",end_time:"2000-01-01T00:00:00+09:00",duration:0,is_free:!0,genres:[],primary_audio_type:"2/0モード(ステレオ)",primary_audio_language:"日本語",secondary_audio_type:null,secondary_audio_language:null,created_at:"2000-01-01T00:00:00+09:00",updated_at:"2000-01-01T00:00:00+09:00"};class _{static async fetchAllVideos(a="desc",e=1){const r=await t.get("/videos",{params:{order:a,page:e}});return r.type==="error"?(t.showGenericError(r,"録画番組一覧を取得できませんでした。"),null):r.data}static async searchVideos(a,e="desc",r=1){const i=await t.get("/videos/search",{params:{query:a,order:e,page:r}});return i.type==="error"?(t.showGenericError(i,"録画番組の検索に失敗しました。"),null):i.data}static async fetchVideo(a){const e=await t.get(`/videos/${a}`);return e.type==="error"?(t.showGenericError(e,"録画番組情報を取得できませんでした。"),null):e.data}static async fetchVideoJikkyoComments(a){const e=await t.get(`/videos/${a}/jikkyo`);return e.type==="error"?(t.showGenericError(e,"過去ログコメントを取得できませんでした。"),{is_success:!1,comments:[],detail:"過去ログコメントを取得できませんでした。"}):(e.data.comments=e.data.comments.filter(r=>s.isMutedComment(r.text,r.author,r.color,r.type,r.size)===!1),e.data)}static async regenerateThumbnail(a,e=!1){const r=await t.post(`/videos/${a}/thumbnail/regenerate`,void 0,{params:{skip_tile_if_exists:e?"true":"false"},timeout:18e5});return r.type==="error"?(t.showGenericError(r,"サムネイルの再生成に失敗しました。"),{is_success:!1,detail:"サムネイルの再生成に失敗しました。"}):r.data}}export{l as I,_ as V};

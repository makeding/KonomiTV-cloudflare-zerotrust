# TLV playback notification contract

DPlayer and tlvdemux own TLV demuxing, playback recovery, and the complete
`tlv_playback_damage` / `tlv_error` event payloads. They do not own HonomiTV's
human-facing error UI.

`PlayerController` is the presentation boundary for those events. It generates
HonomiTV's copy and displays it through the current DPlayer instance's public
`notice()` API, which is the lower-left notice inside the player:

- every severe `tlv_playback_damage` is shown through the current DPlayer
  instance's lower-left `notice()` UI;
- the message identifies the damaged recording or live stream, explains
  whether playback will skip, wait, or stop, gives the next action, and keeps
  the stable `TLV_SOURCE_DAMAGE` code;
- every `tlv_error` keeps the concrete failure reason and is shown through the
  same lower-left in-player notice;
- repeated callbacks for one damaged interval are deduplicated within one
  `PlayerController.init()` generation, and a later initialization may notify
  again;
- DPlayer's TLV core must not invent copy or automatically display TLV failures;
  the HonomiTV adapter is the sole caller of `notice()` for these events;
- HonomiTV's global `Message` Snackbar/Toast must never be used for TLV
  failures, so TLV failures stay inside the player and cannot stack with global
  application notifications.

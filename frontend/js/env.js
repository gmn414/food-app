/* ══════════════════════════════════════
   Runtime config — API base URL
   Deploy: edit the production URL below
   ══════════════════════════════════════ */

(function () {
  var isLocal =
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === '';

  // 本地开发使用 localhost，部署后使用 Render 地址
  if (isLocal) {
    window.API_BASE_URL = 'http://127.0.0.1:8000';
  } else {
    // 部署时改成你的 Render 后端地址，例如:
    // window.API_BASE_URL = 'https://food-app-api.onrender.com';
    window.API_BASE_URL = 'https://food-app-api.onrender.com';
  }
})();

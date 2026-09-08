document.addEventListener("DOMContentLoaded", function () {
  if (!sessionStorage.getItem("logueado")) {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("btnLogout").addEventListener("click", function () {
    sessionStorage.clear();
    limpiarColecciones().finally(function () {
      window.location.href = "index.html";
    });
  });
});
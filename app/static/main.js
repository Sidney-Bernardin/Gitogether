document.body.addEventListener("htmx:responseError", (e) => {
  alert(e.detail.xhr.responseText);
});

document
  .querySelectorAll("form")
  .forEach((f) =>
    f.addEventListener("submit", () =>
      f.querySelectorAll(".err").forEach((e) => e.remove()),
    ),
  );

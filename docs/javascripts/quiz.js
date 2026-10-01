(function () {
  "use strict";

  var TIEN_TO = "cpp-interview-short-term:diem:";

  function luuDiem(bai, diem, tong) {
    try {
      localStorage.setItem(TIEN_TO + bai, JSON.stringify({ diem: diem, tong: tong }));
    } catch (e) {
      /* không lưu được thì thôi, trang vẫn dùng được */
    }
  }

  function docDiem(bai) {
    try {
      var v = localStorage.getItem(TIEN_TO + bai);
      return v ? JSON.parse(v) : null;
    } catch (e) {
      return null;
    }
  }

  function moTa(d) {
    return d ? d.diem + "/" + d.tong : "chưa làm";
  }

  function khoiTaoQuiz(quiz) {
    if (quiz.getAttribute("data-khoi-tao") === "1") return;
    quiz.setAttribute("data-khoi-tao", "1");

    var bai = quiz.getAttribute("data-bai");
    var cauHoi = Array.prototype.slice.call(quiz.querySelectorAll(".cau-hoi"));
    var ketQua = document.createElement("div");
    ketQua.className = "quiz-ket-qua";
    quiz.appendChild(ketQua);
    var diem = 0;
    var daTraLoi = 0;
    var cacXaoTron = [];

    function capNhatKetQua() {
      ketQua.innerHTML = "";
      var p = document.createElement("p");
      if (daTraLoi === cauHoi.length) {
        p.textContent = "Bạn đúng " + diem + "/" + cauHoi.length + " câu.";
      } else {
        var truoc = docDiem(bai);
        p.textContent = truoc
          ? "Lần làm trước: " + moTa(truoc)
          : "Chọn một đáp án cho mỗi câu.";
      }
      ketQua.appendChild(p);
      if (daTraLoi > 0) {
        var nut = document.createElement("button");
        nut.type = "button";
        nut.className = "md-button";
        nut.textContent = "Làm lại";
        nut.addEventListener("click", lamLai);
        ketQua.appendChild(nut);
      }
    }

    function lamLai() {
      diem = 0;
      daTraLoi = 0;
      cauHoi.forEach(function (ch) {
        ch.classList.remove("da-tra-loi");
        ch.querySelectorAll("li").forEach(function (li) {
          li.classList.remove("chon-dung", "chon-sai", "la-dap-an");
        });
        var gt = ch.querySelector(".giai-thich");
        if (gt) gt.classList.remove("hien");
      });
      cacXaoTron.forEach(function (xao) {
        xao();
      });
      capNhatKetQua();
    }

    cauHoi.forEach(function (ch) {
      var dapAn = parseInt(ch.getAttribute("data-dap-an"), 10);
      var cacUl = ch.querySelectorAll("ul");
      var ul = cacUl.length ? cacUl[cacUl.length - 1] : null;
      var luaChon = ul ? Array.prototype.slice.call(ul.children).filter(function (n) {
        return n.tagName === "LI";
      }) : [];
      var giaiThich = ch.querySelector(".giai-thich");
      /* Nhớ phần tử đúng theo thứ tự GỐC (data-dap-an tính từ 1) trước khi xáo. */
      var liDung = luaChon[dapAn - 1] || null;

      function xaoTron() {
        if (!ul || luaChon.length < 2) return;
        var thuTu = luaChon.slice();
        for (var i = thuTu.length - 1; i > 0; i--) {
          var j = Math.floor(Math.random() * (i + 1));
          var tam = thuTu[i];
          thuTu[i] = thuTu[j];
          thuTu[j] = tam;
        }
        thuTu.forEach(function (li) {
          ul.appendChild(li);
        });
      }
      cacXaoTron.push(xaoTron);
      xaoTron();

      luaChon.forEach(function (li) {
        function chon() {
          if (ch.classList.contains("da-tra-loi")) return;
          ch.classList.add("da-tra-loi");
          daTraLoi += 1;
          var dung = li === liDung;
          if (dung) diem += 1;
          li.classList.add(dung ? "chon-dung" : "chon-sai");
          if (liDung) liDung.classList.add("la-dap-an");
          if (giaiThich) giaiThich.classList.add("hien");
          if (daTraLoi === cauHoi.length) luuDiem(bai, diem, cauHoi.length);
          capNhatKetQua();
        }
        li.setAttribute("tabindex", "0");
        li.setAttribute("role", "button");
        li.addEventListener("click", chon);
        li.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            chon();
          }
        });
      });
    });

    capNhatKetQua();
  }

  function dienTienDo() {
    document.querySelectorAll(".diem[data-bai]").forEach(function (el) {
      var d = docDiem(el.getAttribute("data-bai"));
      el.textContent = moTa(d);
      el.classList.toggle("yeu", !!d && d.diem / d.tong < 0.7);
    });
  }

  function chay() {
    document.querySelectorAll(".quiz").forEach(khoiTaoQuiz);
    dienTienDo();
  }

  if (window.document$ && window.document$.subscribe) {
    window.document$.subscribe(chay);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", chay);
  } else {
    chay();
  }
})();

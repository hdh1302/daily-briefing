/**
 * Google Apps Script: IN ĐẬM TOÀN BỘ PHẦN TIÊU ĐỀ CÂU HỎI (TỪ CÂU 63 ĐẾN 84)
 * 
 * Script này sẽ tự động cập nhật tiêu đề tất cả câu hỏi thành chữ in đậm (Bold)
 * giống hệt như các câu từ 60 trở về trước.
 */

function makeAllQuestionsBold() {
  var form = FormApp.getActiveForm();
  var items = form.getItems(FormApp.ItemType.MULTIPLE_CHOICE);
  
  var questionsMap = {
    63: {
      title: "**Câu 63. Compressed layers of decayed plant matter formed the thick ______ that covers the site.**",
      options: ["A. grasses", "B. peat", "C. structures", "D. items"],
      correct: "B. peat"
    },
    64: {
      title: "**Câu 64. A ______ in certain nutrients may have weakened the crops grown in that soil.**",
      options: ["A. acidity", "B. recovery", "C. deficiency", "D. formation"],
      correct: "C. deficiency"
    },
    65: {
      title: "**Câu 65. The new farming method replaced its less efficient ______.**",
      options: ["A. predecessor", "B. innovation", "C. assumption", "D. formation"],
      correct: "A. predecessor"
    },
    66: {
      title: "**Câu 66. Researchers initially ______ the site was a burial ground before further evidence emerged.**",
      options: ["A. undertake", "B. assume", "C. predate", "D. accumulate"],
      correct: "B. assume"
    },
    67: {
      title: "**Câu 67. The introduction of rotational grazing was seen as a major agricultural ______.**",
      options: ["A. deficiency", "B. predecessor", "C. innovation", "D. recovery"],
      correct: "C. innovation"
    },
    68: {
      title: "**Câu 68. Fragments of ancient ______ were found scattered across the settlement.**",
      options: ["A. items", "B. structures", "C. pottery", "D. formations"],
      correct: "C. pottery"
    },
    69: {
      title: "**Câu 69. Passengers were asked to ______ from the boat carefully onto the muddy bank.**",
      options: ["A. alight", "B. undertake", "C. assume", "D. predate"],
      correct: "A. alight"
    },
    70: {
      title: "**Câu 70. The farm was divided into several small ______ to allow controlled grazing.**",
      options: ["A. paddocks", "B. settlements", "C. formations", "D. storages"],
      correct: "A. paddocks"
    },
    71: {
      title: "**Câu 71. Farmers used ______ to prevent any single field from being overused.**",
      options: ["A. overgrazing", "B. rotational grazing", "C. carbon dating", "D. storage"],
      correct: "B. rotational grazing"
    },
    72: {
      title: "**Câu 72. ______ left the land bare and vulnerable to erosion.**",
      options: ["A. Rotational grazing", "B. Carbon dating", "C. Storage", "D. Overgrazing"],
      correct: "D. Overgrazing"
    },
    73: {
      title: "**Câu 73. It took the damaged pasture several years to make a full ______.**",
      options: ["A. recovery", "B. decay", "C. deficiency", "D. formation"],
      correct: "A. recovery"
    },
    74: {
      title: "**Câu 74. After the fire, ______ of the grassland began within just a few weeks.**",
      options: ["A. decay", "B. regrowth", "C. deficiency", "D. formation"],
      correct: "B. regrowth"
    },
    75: {
      title: "**Câu 75. The ancient structure may have provided ______ for both people and livestock.**",
      options: ["A. storage", "B. shelter", "C. recovery", "D. regrowth"],
      correct: "B. shelter"
    },
    76: {
      title: "**Câu 76. The settlement appears to have been abandoned quite ______, with tools left behind.**",
      options: ["A. abruptly", "B. subsequently", "C. intensively", "D. sustainably"],
      correct: "A. abruptly"
    },
    77: {
      title: "**Câu 77. The exact ______ surrounding the site's abandonment remain unclear.**",
      options: ["A. formations", "B. settlements", "C. circumstances", "D. recoveries"],
      correct: "C. circumstances"
    },
    78: {
      title: "**Câu 78. The sudden ______ of the village puzzled archaeologists for years.**",
      options: ["A. abandonment", "B. recovery", "C. regrowth", "D. formation"],
      correct: "A. abandonment"
    },
    79: {
      title: "**Câu 79. ______ farming methods can quickly exhaust the nutrients in the soil.**",
      options: ["A. Sustainable", "B. Intensive", "C. Wetter", "D. Abrupt"],
      correct: "B. Intensive"
    },
    80: {
      title: "**Câu 80. Farmers were encouraged to adopt more ______ grazing practices to protect the land long-term.**",
      options: ["A. intensive", "B. abrupt", "C. sustainable", "D. wetter"],
      correct: "C. sustainable"
    },
    81: {
      title: "**Câu 81. Increasing ______ may have forced early farmers to abandon less fertile land.**",
      options: ["A. climatic pressure", "B. rotational grazing", "C. carbon dating", "D. storage"],
      correct: "A. climatic pressure"
    },
    82: {
      title: "**Câu 82. The climate became noticeably ______ in the centuries following the settlement's decline.**",
      options: ["A. stricter", "B. wetter", "C. healthier", "D. common"],
      correct: "B. wetter"
    },
    83: {
      title: "**Câu 83. Several household ______ were recovered from the site, remarkably well preserved.**",
      options: ["A. structures", "B. formations", "C. items", "D. settlements"],
      correct: "C. items"
    },
    84: {
      title: "**Câu 84. The cold, wet conditions of the bog kept the wooden tools remarkably well ______.**",
      options: ["A. decayed", "B. accumulated", "C. assumed", "D. preserved"],
      correct: "D. preserved"
    }
  };

  for (var i = 0; i < items.length; i++) {
    var mcItem = items[i].asMultipleChoiceItem();
    var currentTitle = mcItem.getTitle();
    var choices = mcItem.getChoices();
    var firstChoice = choices.length > 0 ? choices[0].getValue() : "";

    for (var num in questionsMap) {
      var target = questionsMap[num];
      // Khớp theo lựa chọn đầu tiên hoặc số thứ tự câu hỏi
      if (firstChoice === target.options[0] || currentTitle.indexOf(num + ".") !== -1) {
        mcItem.setTitle(target.title);
        
        var newChoices = [];
        for (var j = 0; j < target.options.length; j++) {
          var opt = target.options[j];
          newChoices.push(mcItem.createChoice(opt, opt === target.correct));
        }
        mcItem.setChoices(newChoices);
        break;
      }
    }
  }

  Logger.log("Đã in đậm toàn bộ câu hỏi thành công!");
}

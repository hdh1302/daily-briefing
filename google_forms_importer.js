/**
 * ==============================================================================
 * BỘ CÔNG CỤ TỰ ĐỘNG TẠO & CẬP NHẬT CÂU HỎI GOOGLE FORM (UNIVERSAL FORMS BUILDER)
 * ==============================================================================
 * Áp dụng cho MỌI loại câu hỏi và đề thi đưa vào Google Forms về sau.
 * 
 * TÍNH NĂNG TỰ ĐỘNG:
 * 1. Tự động in đậm (Bold) toàn bộ tiêu đề câu hỏi.
 * 2. Tự động gắn đáp án đúng (Answer Key) cho chế độ Bài kiểm tra (Quiz).
 * 3. Hỗ trợ 2 cách nhập:
 *    - Cách 1: Dán văn bản thô (Raw Text) - Tự động nhận diện A, B, C, D và đáp án.
 *    - Cách 2: Danh sách cấu trúc (Structured Array).
 */

// ==============================================================================
// 1. HÀM DÙNG NHANH: DÁN VĂN BẢN ĐỀ THI & CHẠY NGAY
// ==============================================================================
function importQuestionsFromRawText() {
  var form = FormApp.getActiveForm();

  // DÁN TOÀN BỘ ĐỀ THI VÀO BIẾN DƯỚI ĐÂY (GIỮ NGUYÊN ĐỊNH DẠNG)
  var rawText = `
Câu 1. Archaeologists ______ several ancient tools while excavating the site. A. observed B. dug up C. assumed D. predated [Key: B]
Câu 2. The excavation took place in a large ______ just outside the village. A. field B. bog C. settlement D. paddock [Key: A]
`;

  var questions = parseRawTextToQuestions(rawText);
  addQuestionsListToForm(form, questions);
}


// ==============================================================================
// 2. HÀM XỬ LÝ CHÍNH: TỰ ĐỘNG IN ĐẬM VÀ TẠO CÂU HỎI
// ==============================================================================
function addQuestionsListToForm(form, questionsList) {
  if (!form) form = FormApp.getActiveForm();

  for (var i = 0; i < questionsList.length; i++) {
    var q = questionsList[i];
    
    // Tự động đảm bảo tiêu đề được in đậm bằng cú pháp **...**
    var title = q.title.trim();
    if (!title.startsWith("**")) title = "**" + title;
    if (!title.endsWith("**")) title = title + "**";

    var item = form.addMultipleChoiceItem();
    item.setTitle(title).setRequired(q.required !== undefined ? q.required : false);

    var choices = [];
    for (var j = 0; j < q.options.length; j++) {
      var opt = q.options[j];
      var isCorrect = false;
      
      // Tự động so khớp đáp án đúng theo ký tự (A, B, C, D) hoặc theo chuỗi
      if (q.correct) {
        var correctKey = q.correct.trim().toUpperCase();
        if (opt.trim().toUpperCase().startsWith(correctKey + ".") || opt.trim().toUpperCase().startsWith(correctKey + " ") || opt === q.correct) {
          isCorrect = true;
        }
      }
      choices.push(item.createChoice(opt, isCorrect));
    }
    item.setChoices(choices);
  }

  Logger.log("✅ Đã tạo thành công " + questionsList.length + " câu hỏi in đậm vào Google Form!");
}


// ==============================================================================
// 3. BỘ PHÂN TÍCH TỰ ĐỘNG TỪ VĂN BẢN (RAW TEXT PARSER)
// ==============================================================================
function parseRawTextToQuestions(text) {
  var lines = text.split("\n");
  var questions = [];
  var currentQ = null;

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim();
    if (!line) continue;

    // Nhận diện dòng bắt đầu câu hỏi (Ví dụ: "Câu 1.", "Question 1:", "1.")
    var matchQuestion = line.match(/^(Câu\s*\d+|Question\s*\d+|\d+)[\.\:](.*)/i);
    if (matchQuestion) {
      if (currentQ) questions.push(currentQ);

      var fullLine = line;
      var key = "";
      
      // Trích xuất đáp án nếu có ghi [Key: A] hoặc (Đ/A: B) ở cuối
      var keyMatch = fullLine.match(/\[(?:Key|Đ\/A|Đáp án)\s*:\s*([A-D])\]/i);
      if (keyMatch) {
        key = keyMatch[1].toUpperCase();
        fullLine = fullLine.replace(keyMatch[0], "").trim();
      }

      // Trích xuất các phương án A, B, C, D
      var optA = "", optB = "", optC = "", optD = "";
      var qText = fullLine;

      var parts = fullLine.split(/(?=\s[A-D]\.\s)/);
      if (parts.length >= 2) {
        qText = parts[0].trim();
        var options = [];
        for (var p = 1; p < parts.length; p++) {
          options.push(parts[p].trim());
        }
        currentQ = {
          title: qText,
          options: options,
          correct: key
        };
      } else {
        currentQ = {
          title: fullLine,
          options: [],
          correct: key
        };
      }
    } else if (currentQ && line.match(/^[A-D]\.\s/)) {
      currentQ.options.push(line);
    }
  }

  if (currentQ) questions.push(currentQ);
  return questions;
}

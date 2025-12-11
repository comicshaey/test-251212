// Phaser 3 기반 Kohaeyoung 미니 RPG
// 너무 복잡하게 안 가고, 텍스트 + 버튼 + 로그 정도만 구현

// 고정 데이터 (정체성, 기면증 모듈)
const identity = {
  name: "Kohaeyoung",
  roles: ["교육행정 실무자", "창작자", "자동화 도구 개발자"],
};

const disease = {
  baselineSleepiness: 60,
  emotionTriggerSensitivity: 80,
  safetyRiskLevel: 70,
};

// 상태값
const state = {
  energy: 50,
  emotion: 40,
  logs: [],
};

// 기면증 모듈 tick
function diseaseTick(emotion, fatigue) {
  const base = disease.baselineSleepiness;
  const sens = disease.emotionTriggerSensitivity;

  let triggerScore = base * 0.4 + emotion * (sens / 100) * 0.3 + fatigue * 0.3;
  triggerScore = Math.max(0, Math.min(100, triggerScore));

  const roll = Math.random() * 100;
  const eventHappened = roll < triggerScore;

  const result = {
    triggerScore: Math.round(triggerScore * 10) / 10,
    sleepAttack: false,
    cataplexy: false,
  };

  if (eventHappened) {
    if (Math.random() < 0.5) {
      result.sleepAttack = true;
    } else {
      result.cataplexy = true;
    }
  }

  return result;
}

function clampState() {
  state.energy = Math.max(0, Math.min(100, state.energy));
  state.emotion = Math.max(0, Math.min(100, state.emotion));
}

// 행동 함수들
function actWork() {
  const before = state.energy;
  state.energy -= 10;
  state.emotion += 5;
  clampState();
  return `행정업무: 에너지 ${before} → ${state.energy}, 감정 ${state.emotion}`;
}

function actCreative() {
  const before = state.energy;
  state.energy -= 6;
  state.emotion += 10;
  clampState();
  return `창작: 에너지 ${before} → ${state.energy}, 감정 ${state.emotion}`;
}

function actNap() {
  const before = state.energy;
  state.energy += 8;
  state.emotion -= 5;
  clampState();
  return `낮잠: 에너지 ${before} → ${state.energy}, 감정 ${state.emotion}`;
}

function actMeltdown() {
  const beforeE = state.energy;
  const beforeEm = state.emotion;
  state.emotion = Math.min(100, state.emotion + 40);
  state.energy = Math.max(0, state.energy - 20);
  clampState();
  return `감정 과부하! 감정 ${beforeEm} → ${state.emotion}, 에너지 ${beforeE} → ${state.energy}`;
}

function actSimulateDay() {
  const fatigue = 100 - state.energy;
  const result = diseaseTick(state.emotion, fatigue);
  const notes = [];

  if (result.sleepAttack) {
    notes.push("수면발작 발생 (갑자기 잠듦)");
    state.energy += 10;
  }
  if (result.cataplexy) {
    notes.push("탈력발작 발생 (감정 자극 후 힘 빠짐)");
    state.energy -= 10;
  }
  if (!result.sleepAttack && !result.cataplexy) {
    notes.push("발작 없이 하루를 버텼다.");
  }
  clampState();

  notes.push(
    `트리거 점수: ${result.triggerScore} (emotion=${state.emotion}, fatigue=${fatigue})`
  );

  return notes;
}

// Phaser 씬 정의
class MainScene extends Phaser.Scene {
  constructor() {
    super("MainScene");
  }

  create() {
    // 배경
    this.cameras.main.setBackgroundColor("#020617");

    // 상단 타이틀
    this.add
      .text(400, 30, "Kohaeyoung RPG · Phaser", {
        fontFamily: "맑은 고딕, sans-serif",
        fontSize: 24,
        color: "#38bdf8",
      })
      .setOrigin(0.5, 0.5);

    // 정체성 텍스트
    const identityText =
      `이름: ${identity.name}\n` +
      `역할: ${identity.roles.join(", ")}\n` +
      `기면증 모듈: baseline=${disease.baselineSleepiness}, sens=${disease.emotionTriggerSensitivity}`;

    this.add
      .text(32, 70, identityText, {
        fontSize: 14,
        color: "#e5e7eb",
      })
      .setOrigin(0, 0);

    // 상태 텍스트
    this.energyText = this.add.text(32, 130, "", {
      fontSize: 16,
      color: "#a5b4fc",
    });
    this.emotionText = this.add.text(32, 155, "", {
      fontSize: 16,
      color: "#a5b4fc",
    });

    // 버튼들 (간단하게 사각형 + 텍스트)
    this.buttons = [];

    this.makeButton(32, 200, "행정업무", () => {
      const msg = actWork();
      this.pushLog("▶ " + msg, "action");
      this.updateStatus();
    });

    this.makeButton(160, 200, "창작", () => {
      const msg = actCreative();
      this.pushLog("▶ " + msg, "action");
      this.updateStatus();
    });

    this.makeButton(288, 200, "낮잠", () => {
      const msg = actNap();
      this.pushLog("▶ " + msg, "action");
      this.updateStatus();
    });

    this.makeButton(416, 200, "과부하", () => {
      const msg = actMeltdown();
      this.pushLog("‼ " + msg, "alert");
      this.updateStatus();
    });

    this.makeButton(544, 200, "하루 시뮬", () => {
      const notes = actSimulateDay();
      this.pushLog("◆ 하루 시뮬레이션", "note");
      notes.forEach((n) => this.pushLog("  · " + n, "note"));
      this.updateStatus();
    });

    this.makeButton(672, 200, "로그 클리어", () => {
      this.logLines = [];
      this.renderLog();
    });

    // 로그 영역
    this.logLines = [];
    this.logText = this.add
      .text(32, 240, "", {
        fontFamily: "JetBrains Mono, ui-monospace, monospace",
        fontSize: 12,
        color: "#e5e7eb",
        lineSpacing: 4,
      })
      .setOrigin(0, 0);

    this.pushLog("[시스템] Kohaeyoung RPG(Phaser) 시작", "system");
    this.updateStatus();
  }

  makeButton(x, y, label, onClick) {
    // 버튼 배경
    const w = 104;
    const h = 32;
    const bg = this.add
      .rectangle(x, y, w, h, 0x0f172a)
      .setOrigin(0, 0)
      .setStrokeStyle(1, 0x1e293b)
      .setInteractive({ useHandCursor: true });

    const text = this.add
      .text(x + w / 2, y + h / 2, label, {
        fontSize: 14,
        color: "#e5e7eb",
      })
      .setOrigin(0.5, 0.5);

    bg.on("pointerover", () => {
      bg.setFillStyle(0x1e293b);
    });
    bg.on("pointerout", () => {
      bg.setFillStyle(0x0f172a);
    });
    bg.on("pointerdown", () => {
      bg.setFillStyle(0x38bdf8);
      text.setColor("#020617");
    });
    bg.on("pointerup", () => {
      bg.setFillStyle(0x1e293b);
      text.setColor("#e5e7eb");
      onClick();
    });

    this.buttons.push({ bg, text });
  }

  updateStatus() {
    this.energyText.setText(`에너지: ${state.energy}`);
    this.emotionText.setText(`감정: ${state.emotion}`);
  }

  pushLog(line, type) {
    // 단순하게 색상만 다르게
    this.logLines.push({ text: line, type });
    // 너무 길어지면 앞에서 자르기
    if (this.logLines.length > 14) {
      this.logLines.shift();
    }
    this.renderLog();
  }

  renderLog() {
    let fullText = "";
    this.logLines.forEach((entry) => {
      fullText += entry.text + "\n";
    });
    this.logText.setText(fullText);
  }
}

// Phaser 게임 설정
const config = {
  type: Phaser.AUTO,
  width: 800,
  height: 480,
  parent: "game-container",
  scene: [MainScene],
  backgroundColor: "#020617",
};

const game = new Phaser.Game(config);

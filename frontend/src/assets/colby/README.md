# COLBY 캐릭터 에셋 폴더

이 폴더에 파일을 넣기만 하면 `AI Human` 화면에 코드 수정 없이 자동으로 반영됩니다.
(`ColbyAvatar.jsx`가 `import.meta.glob`으로 이 폴더를 통째로 읽어서, 상태에 맞는 파일명을 찾아 보여줍니다.)

## 현재 상태 (2026-08-13 기준)

- `colby-idle.png` — 적용 완료. idle / listening / thinking 상태는 지금 전부 이 이미지를 함께 씁니다.
- speaking 전용 3장 적용 완료 → speaking 상태에서 닫힘→살짝 벌림→활짝 벌림→살짝 벌림 순서로
  자연스럽게 반복되는 mouth animation이 동작합니다 (`useSpeakingMouth.js`).

## 필요한 파일명

| 상태 | 파일명 | 비고 |
|---|---|---|
| idle / listening / thinking (공용) | `colby-idle.png` | ✅ 적용됨. listening·thinking 전용 이미지를 원하면 각각 `colby-listening.png`, `colby-thinking.png`로 추가 가능(선택) |
| speaking — 입 닫힘 | `colby-speaking-closed.png` | mouth animation 프레임 1 |
| speaking — 입 살짝 벌림 | `colby-speaking-half.png` | mouth animation 프레임 2 |
| speaking — 입 활짝 벌림 | `colby-speaking-open.png` | mouth animation 프레임 3. 세 파일이 160ms 간격으로 0→1→2→1 순서로 반복 표시됨 |

## 이미지 규격 권장

- 형식: PNG(배경 투명 권장), WebP/JPG도 인식됨
- speaking 두 장은 **같은 구도·같은 크기**로 만들어야 전환할 때 캐릭터가 흔들리지 않습니다 (입 모양만 다르게)
- 배치: 좌측 무대(`avatar-container`) 안에서 `object-fit: contain`으로 비율 유지된 채 중앙에 표시됩니다.

## 파일이 없을 때

이미지가 하나도 없으면 "COLBY CHARACTER ASSET" 플레이스홀더가 표시되고,
상태 전용 이미지가 없으면 `colby-idle.png`로 자동 대체됩니다. 깨진 이미지 아이콘은 뜨지 않습니다.

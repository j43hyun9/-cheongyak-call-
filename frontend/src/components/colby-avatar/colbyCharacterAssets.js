import { COLBY_STATES } from './useColbyState';

// src/assets/colby/ 폴더의 이미지를 전부 glob으로 가져온다.
// 파일이 하나도 없어도 빈 객체만 반환될 뿐 빌드/실행 에러가 나지 않는다.
// → 나중에 실제 이미지를 폴더에 넣기만 하면 이 코드 수정 없이 자동으로 인식됨.
const assetModules = import.meta.glob('../../assets/colby/*.{png,webp,jpg,jpeg}', {
  eager: true,
  import: 'default',
});

// 상태별 기본 파일명 매핑 (README.md와 동일한 규격)
export const COLBY_STATE_FILENAMES = {
  [COLBY_STATES.IDLE]: 'colby-idle.png',
  [COLBY_STATES.LISTENING]: 'colby-listening.png',
  [COLBY_STATES.THINKING]: 'colby-thinking.png',
  [COLBY_STATES.SPEAKING]: 'colby-speaking-closed.png',
};

// speaking 상태에서 mouth animation(닫음→살짝→활짝 3단계)에 쓰는 프레임.
// useSpeakingMouth 훅이 만든 frameIndex(0|1|2)로 이 배열을 인덱싱한다.
// 파일이 아직 없으면 getColbyImage()가 자동으로 idle 이미지로 대체한다.
export const COLBY_SPEAKING_FRAMES = [
  'colby-speaking-closed.png',
  'colby-speaking-half.png',
  'colby-speaking-open.png',
];

function findAsset(filename) {
  const entry = Object.entries(assetModules).find(([path]) => path.endsWith(`/${filename}`));
  return entry ? entry[1] : null;
}

// 상태(+ speaking 프레임 인덱스)에 해당하는 이미지 URL.
// 상태 전용 이미지가 아직 없으면 idle 이미지로 대체하고(현재는 이미지 한 장으로
// 모든 상태를 표현하는 단계), idle 이미지조차 없으면 null(플레이스홀더 표시).
export function getColbyImage(state, speakingFrameIndex = 0) {
  const idleAsset = findAsset(COLBY_STATE_FILENAMES[COLBY_STATES.IDLE]);

  if (state === COLBY_STATES.SPEAKING) {
    const filename = COLBY_SPEAKING_FRAMES[speakingFrameIndex % COLBY_SPEAKING_FRAMES.length];
    return (
      findAsset(filename) ??
      findAsset(COLBY_STATE_FILENAMES[COLBY_STATES.SPEAKING]) ??
      idleAsset
    );
  }

  return findAsset(COLBY_STATE_FILENAMES[state]) ?? idleAsset;
}

// 플레이스홀더에 "이 파일을 넣으면 됩니다"라고 안내하기 위한 파일명 조회.
export function getColbyImageFilename(state) {
  return COLBY_STATE_FILENAMES[state] ?? COLBY_STATE_FILENAMES[COLBY_STATES.IDLE];
}

import { COLBY_STATES } from './useColbyState';

const assetModules = import.meta.glob('../../assets/colby/*.{png,webp,jpg,jpeg}', {
  eager: true,
  import: 'default',
});

export const COLBY_STATE_FILENAMES = {
  [COLBY_STATES.IDLE]: 'colby-idle.png',
  [COLBY_STATES.LISTENING]: 'colby-listening.png',
  [COLBY_STATES.THINKING]: 'colby-thinking.png',
  [COLBY_STATES.SPEAKING]: 'colby-speaking-closed.png',
};

export const COLBY_MOUTH_FRAMES = {
  closed:  'colby-speaking-closed.png',
  open:    'colby-speaking-open.png',
  ae:      'colby-speaking-ae.png',
  eo:      'colby-speaking-eo.png',
  mid:     'colby-speaking-half.png',
  eu:      'colby-speaking-eu.png',
  wide:    'colby-speaking-wide.png',
  round:   'colby-speaking-round.png',
  pucker:  'colby-speaking-pucker.png',
};

const MOUTH_FALLBACK = { ae: 'open', eo: 'open', eu: 'wide' };

function findAsset(filename) {
  const entry = Object.entries(assetModules).find(([path]) => path.endsWith(`/${filename}`));
  return entry ? entry[1] : null;
}

export function getColbyImage(state, mouthKey = 'closed') {
  const idleAsset = findAsset(COLBY_STATE_FILENAMES[COLBY_STATES.IDLE]);

  if (state === COLBY_STATES.SPEAKING) {
    const filename = COLBY_MOUTH_FRAMES[mouthKey] ?? COLBY_MOUTH_FRAMES.closed;
    const fallbackFilename = MOUTH_FALLBACK[mouthKey] ? COLBY_MOUTH_FRAMES[MOUTH_FALLBACK[mouthKey]] : null;
    return (
      findAsset(filename) ??
      (fallbackFilename ? findAsset(fallbackFilename) : null) ??
      idleAsset
    );
  }

  return findAsset(COLBY_STATE_FILENAMES[state]) ?? idleAsset;
}

export function getColbyImageFilename(state) {
  return COLBY_STATE_FILENAMES[state] ?? COLBY_STATE_FILENAMES[COLBY_STATES.IDLE];
}

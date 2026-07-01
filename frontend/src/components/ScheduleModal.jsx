import { useState } from 'react';

export default function ScheduleModal({
  mode, schedule, ipo, defaultDate, onSave, onDelete, onClose,
}) {
  const [title, setTitle]       = useState(schedule?.title ?? '');
  const [datetime, setDatetime] = useState(
    schedule?.datetime?.slice(0, 16) ??
    (defaultDate ? `${defaultDate}T09:00` : ''),
  );

  // IPO 상세 보기 (읽기 전용)
  if (mode === 'ipo-info') {
    return (
      <Overlay onClose={onClose}>
        <h3>📋 {ipo?.name}</h3>
        <div className="ipo-info-list">
          <p>📅 청약 기간: {ipo?.start} ~ {ipo?.end}</p>
          {ipo?.price != null && <p>💰 공모가: {ipo.price.toLocaleString()}원</p>}
          {ipo?.underwriter && <p>🏦 주관사: {ipo.underwriter}</p>}
        </div>
        <p className="ipo-notice">
          ⚠️ 투자 판단은 직접 해주세요. 콜비는 정보만 안내해요!
        </p>
        <div className="modal-actions">
          <button className="btn-save" onClick={onClose}>확인</button>
        </div>
      </Overlay>
    );
  }

  const isEdit = mode === 'edit';

  const onSubmit = (e) => {
    e.preventDefault();
    if (!title.trim() || !datetime) return;
    onSave({ id: schedule?.id, title: title.trim(), datetime });
  };

  return (
    <Overlay onClose={onClose}>
      <h3>{isEdit ? '✏️ 일정 수정' : '➕ 일정 추가'}</h3>
      <form onSubmit={onSubmit}>
        <label htmlFor="sch-title">제목</label>
        <input
          id="sch-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="일정 제목"
          required
          autoFocus
        />
        <label htmlFor="sch-dt">날짜 · 시간</label>
        <input
          id="sch-dt"
          type="datetime-local"
          value={datetime}
          onChange={(e) => setDatetime(e.target.value)}
          required
        />
        <div className="modal-actions">
          {isEdit && (
            <button
              type="button"
              className="btn-delete"
              onClick={() => onDelete(schedule.id)}
            >
              삭제
            </button>
          )}
          <button type="button" className="btn-cancel" onClick={onClose}>
            취소
          </button>
          <button type="submit" className="btn-save">
            저장
          </button>
        </div>
      </form>
    </Overlay>
  );
}

function Overlay({ children, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}

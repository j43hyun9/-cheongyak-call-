import { useState, useEffect, useCallback, useRef } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';
import koLocale from '@fullcalendar/core/locales/ko';
import {
  getIpoSchedule, getSchedules,
  createSchedule, updateSchedule, deleteSchedule,
} from '../api';
import ScheduleModal from '../components/ScheduleModal';

export default function CalendarPage() {
  const calRef = useRef(null);
  const [events, setEvents]       = useState([]);
  const [view, setView]           = useState('dayGridMonth');
  const [modal, setModal]         = useState(null);
  const [loadingMsg, setLoadingMsg] = useState('');

  const loadEvents = useCallback(async () => {
    setLoadingMsg('📡 일정 불러오는 중...');
    try {
      const [ipoRes, schedRes] = await Promise.all([
        getIpoSchedule('all'),
        getSchedules(),
      ]);

      const ipoEvents = (ipoRes.items ?? []).map((item) => ({
        id: `ipo-${item.name}`,
        title: `📋 ${item.name}`,
        start: item.start,
        end: addOneDay(item.end), // FullCalendar end는 exclusive
        color: '#3b82f6',
        extendedProps: { type: 'ipo', ...item },
      }));

      const personalEvents = (schedRes ?? []).map((s) => ({
        id: `sched-${s.id}`,
        title: `✅ ${s.title}`,
        start: s.datetime,
        color: '#22c55e',
        extendedProps: { type: 'personal', schedId: s.id, title: s.title, datetime: s.datetime },
      }));

      setEvents([...ipoEvents, ...personalEvents]);
    } finally {
      setLoadingMsg('');
    }
  }, []);

  useEffect(() => { loadEvents(); }, [loadEvents]);

  const changeView = (v) => {
    setView(v);
    calRef.current?.getApi().changeView(v);
  };

  const handleDateClick = (info) => {
    setModal({ mode: 'add', defaultDate: info.dateStr });
  };

  const handleEventClick = (info) => {
    const p = info.event.extendedProps;
    if (p.type === 'ipo') {
      setModal({ mode: 'ipo-info', ipo: p });
    } else {
      setModal({
        mode: 'edit',
        schedule: { id: p.schedId, title: p.title, datetime: p.datetime },
      });
    }
  };

  const handleSave = async ({ id, title, datetime }) => {
    try {
      if (id) {
        await updateSchedule(id, title, datetime);
      } else {
        await createSchedule(title, datetime);
      }
      await loadEvents();
      setModal(null);
    } catch {
      alert('저장 중 오류가 발생했어요 😢');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('이 일정을 삭제할까요?')) return;
    try {
      await deleteSchedule(id);
      await loadEvents();
      setModal(null);
    } catch {
      alert('삭제 중 오류가 발생했어요 😢');
    }
  };

  return (
    <div className="calendar-page">
      <div className="calendar-header">
        <h2>📅 공모주 · 내 일정</h2>
        <div className="legend-group">
          <span className="legend-ipo">■ 공모주 청약</span>
          <span className="legend-personal">■ 내 일정</span>
        </div>
        <div className="view-toggle">
          <button
            className={view === 'dayGridMonth' ? 'active' : ''}
            onClick={() => changeView('dayGridMonth')}
          >월간</button>
          <button
            className={view === 'listMonth' ? 'active' : ''}
            onClick={() => changeView('listMonth')}
          >목록</button>
        </div>
        <button
          className="btn-add-schedule"
          onClick={() =>
            setModal({ mode: 'add', defaultDate: new Date().toISOString().slice(0, 10) })
          }
        >
          + 일정 추가
        </button>
      </div>

      {loadingMsg && <p className="loading-msg">{loadingMsg}</p>}

      <FullCalendar
        ref={calRef}
        plugins={[dayGridPlugin, listPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        locale={koLocale}
        events={events}
        dateClick={handleDateClick}
        eventClick={handleEventClick}
        headerToolbar={{ left: 'prev,next today', center: 'title', right: '' }}
        buttonText={{ today: '오늘' }}
        height="auto"
      />

      {modal && (
        <ScheduleModal
          mode={modal.mode}
          schedule={modal.schedule}
          ipo={modal.ipo}
          defaultDate={modal.defaultDate}
          onSave={handleSave}
          onDelete={handleDelete}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}

function addOneDay(dateStr) {
  if (!dateStr) return undefined;
  const d = new Date(dateStr);
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

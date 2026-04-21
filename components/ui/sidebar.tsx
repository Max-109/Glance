import { SECTION_GROUPS, type BridgeState, type SectionId } from "@/lib/glance-bridge";

import { Icon } from "../icons";

import { Indicator } from "./indicator";

const RUNTIME_LABELS: Record<string, string> = {
  idle: "Idle",
  listening: "Listening",
  processing: "Processing",
  speaking: "Speaking",
  ready: "Ready",
  error: "Error",
};

export function Sidebar({
  state,
  onSelectSection,
}: {
  state: BridgeState;
  onSelectSection: (section: SectionId) => void;
}) {
  const runtimeLabel = RUNTIME_LABELS[state.runtimeState] || RUNTIME_LABELS.idle;

  return (
    <aside className="sidebar-shell">
      <div className="sidebar-brand">
        <Indicator
          state={state.runtimeState}
          message={state.runtimeMessage}
          size="large"
          label={`Glance live state: ${runtimeLabel}`}
        />
        <div className="sidebar-brand__copy">
          <p className="sidebar-brand__title">Glance</p>
          <p className="sidebar-brand__status">{runtimeLabel}</p>
        </div>
      </div>

      {SECTION_GROUPS.map((group) => (
        <section className="sidebar-group" key={group.items[0]?.id ?? "group"}>
          {group.label ? <p className="sidebar-group__label">{group.label}</p> : null}
          <div className="sidebar-group__items">
            {group.items.map((item) => {
              const selected = state.currentSection === item.id;
              return (
                <button
                  type="button"
                  key={item.id}
                  className={`sidebar-item${selected ? " is-selected" : ""}`}
                  aria-current={selected ? "page" : undefined}
                  onClick={() => onSelectSection(item.id)}
                >
                  <span className="sidebar-item__icon">
                    <Icon name={item.icon} />
                  </span>
                  <span>{item.title}</span>
                </button>
              );
            })}
          </div>
        </section>
      ))}

      <section className="runtime-card" aria-label="Live status">
        <div className="runtime-card__label">Live</div>
        <div className="runtime-card__value">{runtimeLabel}</div>
        <p className="runtime-card__message">{state.runtimeMessage}</p>
      </section>
    </aside>
  );
}

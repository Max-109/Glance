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
          <span className="sidebar-brand__pill">
            <span className="sidebar-brand__pill-dot" />
            <span>{runtimeLabel}</span>
          </span>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Sections">
        {SECTION_GROUPS.map((group, groupIndex) => (
          <section className="sidebar-group" key={group.items[0]?.id ?? `group-${groupIndex}`}>
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
                    <span className="sidebar-item__rail" aria-hidden="true" />
                    <span className="sidebar-item__icon">
                      <Icon name={item.icon} />
                    </span>
                    <span className="sidebar-item__label">{item.title}</span>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </nav>
    </aside>
  );
}

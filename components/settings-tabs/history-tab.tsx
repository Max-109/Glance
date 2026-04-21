import { Button } from "../ui/button";
import { NumberInput } from "../ui/number-input";
import { Panel } from "../ui/panel";

import { HistoryPreviewCard } from "./history-preview-card";
import type { SettingsTabProps } from "./shared";

export function HistoryTab({
  state,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onRunAction,
  getDraftValue,
}: Pick<
  SettingsTabProps,
  | "state"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "onRunAction"
  | "getDraftValue"
>) {
  const hasSessions = state.historyPreview.length > 0;
  const status = hasSessions
    ? { tone: "accent" as const, label: "Recent activity" }
    : { tone: "neutral" as const, label: "No saved sessions yet" };

  return (
    <div className="stack">
      <Panel
        title="History"
        description="Choose how much to keep and peek at recent sessions."
        status={status}
        footer={
          <>
            <Button
              label="Delete history"
              icon="trash"
              variant="danger"
              onClick={() => {
                if (!window.confirm("Delete all saved history on this device?")) {
                  return;
                }
                onRunAction("clearHistory");
              }}
            />
            <div className="inline-note inline-note--end">This cannot be undone.</div>
          </>
        }
      >
        <NumberInput
          fieldName="history_length"
          label="History Limit"
          icon="history"
          inputMode="numeric"
          step={1}
          min={1}
          value={getDraftValue("history_length")}
          errorText={state.errors.history_length}
          helperText="Max number of saved sessions."
          onChange={(value) => onDraftChange("history_length", value)}
          onCommit={(value) => onDraftCommit("history_length", value)}
          onFocus={() => onDraftFocus("history_length")}
        />

        {hasSessions ? (
          <div className="history-preview" aria-label="Recent saved sessions">
            {state.historyPreview.map((item) => (
              <HistoryPreviewCard key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <div className="history-empty">
            <strong>Nothing here yet</strong>
            <span>Sessions show up after you use Live, Quick Ask, or Read Screen.</span>
          </div>
        )}
      </Panel>
    </div>
  );
}

import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { NumberInput } from "../ui/number-input";

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
  return (
    <Card
      title="History"
      description="Choose how much history to keep."
      footer={
        <div className="card-actions card-actions--stack">
          <div className="section-callout">
            <strong>Delete history</strong>
          </div>
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
        </div>
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
        onChange={(value) => onDraftChange("history_length", value)}
        onCommit={(value) => onDraftCommit("history_length", value)}
        onFocus={() => onDraftFocus("history_length")}
      />

      {state.historyPreview.length ? (
        <div className="history-preview" aria-label="Recent saved sessions">
          {state.historyPreview.map((item) => (
            <HistoryPreviewCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <div className="history-empty">
          <strong>No saved sessions yet</strong>
          <span>Recent sessions will appear here after you use Glance.</span>
        </div>
      )}
    </Card>
  );
}

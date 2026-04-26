import { useMemo, useState } from "react";

import { Icon } from "@/components/icons";
import { GlanceButton } from "@/components/settings-shell/button";
import { StatusBadge } from "@/components/settings-shell/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { MemoryItem } from "@/lib/glance-bridge";
import { cn } from "@/lib/utils";

import type { SettingsTabProps } from "./shared";

function formatMemoryDate(value: string) {
  if (!value) return "Saved just now";
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function memorySummary(memories: MemoryItem[]) {
  if (memories.length === 0) return "No memories yet";
  if (memories.length === 1) return "1 memory";
  return `${memories.length} memories`;
}

export function MemoriesTab({
  state,
  onRunAction,
}: Pick<SettingsTabProps, "state" | "onRunAction">) {
  const [editingId, setEditingId] = useState("");
  const [draft, setDraft] = useState({
    title: "",
    description: "",
    intent: "",
  });
  const memories = state.memories;
  const latestSavedAt = memories[0]?.createdAt ?? "";
  const hasMemories = memories.length > 0;
  const countLabel = useMemo(() => memorySummary(memories), [memories]);

  function startEditing(memory: MemoryItem) {
    setEditingId(memory.id);
    setDraft({
      title: memory.title,
      description: memory.description,
      intent: memory.intent,
    });
  }

  function cancelEditing() {
    setEditingId("");
    setDraft({ title: "", description: "", intent: "" });
  }

  function saveMemory(memoryId: string) {
    onRunAction("updateMemory", {
      memoryId,
      title: draft.title,
      description: draft.description,
      intent: draft.intent,
    });
    cancelEditing();
  }

  function deleteMemory(memory: MemoryItem) {
    if (!window.confirm(`Delete “${memory.title}”?`)) {
      return;
    }
    onRunAction("deleteMemory", { memoryId: memory.id });
    if (editingId === memory.id) {
      cancelEditing();
    }
  }

  return (
    <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
      <CardHeader className="border-b border-border px-5 py-4">
        <div className="flex min-w-0 items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-4">
            <span className="grid size-12 shrink-0 place-items-center rounded-2xl border border-[var(--panel-border)] bg-[var(--chip-bg-soft)] text-[var(--accent-strong)]">
              <Icon name="memory" className="size-5" />
            </span>
            <div className="min-w-0">
              <div className="flex min-w-0 flex-wrap items-center gap-3">
                <CardTitle className="text-base font-semibold">Memories</CardTitle>
                <StatusBadge tone={hasMemories ? "accent" : "neutral"}>
                  {countLabel}
                </StatusBadge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {hasMemories
                  ? `Latest saved ${formatMemoryDate(latestSavedAt)}`
                  : "Saved notes will show up here."}
              </p>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-5 py-5">
        {hasMemories ? (
          <section className="grid gap-3" aria-label="Saved memories">
            {memories.map((memory) => {
              const editing = editingId === memory.id;
              return (
                <article
                  key={memory.id}
                  className={cn(
                    "grid gap-4 rounded-2xl border border-[var(--panel-border)] bg-[var(--panel-bg-deep)] p-4 [content-visibility:auto] [contain-intrinsic-size:1px_13rem]",
                    editing &&
                      "border-[color-mix(in_srgb,var(--accent)_42%,transparent)]",
                  )}
                >
                  {editing ? (
                    <MemoryEditor
                      draft={draft}
                      onChange={setDraft}
                      onCancel={cancelEditing}
                      onSave={() => saveMemory(memory.id)}
                    />
                  ) : (
                    <MemoryView
                      memory={memory}
                      onEdit={() => startEditing(memory)}
                      onDelete={() => deleteMemory(memory)}
                    />
                  )}
                </article>
              );
            })}
          </section>
        ) : (
          <div className="rounded-2xl border border-border bg-card p-5">
            <span className="mb-4 grid size-12 place-items-center rounded-2xl border border-white/10 bg-white/[0.035] text-[var(--text-muted)]">
              <Icon name="memory" className="size-5" />
            </span>
            <strong className="block text-sm font-semibold text-foreground">
              Nothing saved yet
            </strong>
            <span className="mt-1 block text-sm text-muted-foreground">
              Ask Glance to remember a task, idea, or note.
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MemoryView({
  memory,
  onEdit,
  onDelete,
}: {
  memory: MemoryItem;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="grid min-w-0 gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
      <div className="min-w-0">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <h3 className="min-w-0 break-words text-base font-semibold text-[var(--text-strong)]">
            {memory.title}
          </h3>
          <span className="rounded-full border border-white/10 bg-white/[0.035] px-2.5 py-1 font-mono text-[0.72rem] font-semibold tabular-nums text-[var(--text-muted)]">
            {formatMemoryDate(memory.createdAt)}
          </span>
        </div>
        <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--text-muted)]">
          {memory.description}
        </p>
        {memory.intent ? (
          <p className="mt-3 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-2 text-sm leading-6 text-[var(--text-strong)]">
            {memory.intent}
          </p>
        ) : null}
      </div>

      <div className="flex items-start gap-2 md:justify-end">
        <GlanceButton
          icon="edit"
          ariaLabel={`Edit ${memory.title}`}
          onClick={onEdit}
        />
        <GlanceButton
          icon="trash"
          variant="danger"
          ariaLabel={`Delete ${memory.title}`}
          onClick={onDelete}
        />
      </div>
    </div>
  );
}

function MemoryEditor({
  draft,
  onChange,
  onCancel,
  onSave,
}: {
  draft: { title: string; description: string; intent: string };
  onChange: (draft: { title: string; description: string; intent: string }) => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  const canSave = Boolean(draft.title.trim() && draft.description.trim());
  return (
    <div className="grid gap-4">
      <div className="grid gap-2">
        <label className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]" htmlFor="memory-title">
          Name
        </label>
        <Input
          id="memory-title"
          name="memory-title"
          value={draft.title}
          maxLength={120}
          autoComplete="off"
          onChange={(event) =>
            onChange({ ...draft, title: event.target.value })
          }
        />
      </div>

      <div className="grid gap-2">
        <label
          className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]"
          htmlFor="memory-description"
        >
          Note
        </label>
        <Textarea
          id="memory-description"
          name="memory-description"
          value={draft.description}
          maxLength={4000}
          autoComplete="off"
          className="min-h-28"
          onChange={(event) =>
            onChange({ ...draft, description: event.target.value })
          }
        />
      </div>

      <div className="grid gap-2">
        <label className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]" htmlFor="memory-intent">
          Intention
        </label>
        <Input
          id="memory-intent"
          name="memory-intent"
          value={draft.intent}
          maxLength={1000}
          autoComplete="off"
          onChange={(event) =>
            onChange({ ...draft, intent: event.target.value })
          }
        />
      </div>

      <div className="flex flex-wrap justify-end gap-2">
        <GlanceButton icon="x" onClick={onCancel}>
          Cancel
        </GlanceButton>
        <GlanceButton
          icon="check"
          variant="primary"
          disabled={!canSave}
          onClick={onSave}
        >
          Save Memory
        </GlanceButton>
      </div>
    </div>
  );
}

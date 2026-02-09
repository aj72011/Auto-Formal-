import { KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { ExampleSuggestions } from "./ExampleSuggestions";

interface EditorContainerProps {
  value: string;
  disabled?: boolean;
  examples: string[];
  onChange: (value: string) => void;
}

export function EditorContainer({
  value,
  disabled = false,
  examples,
  onChange,
}: EditorContainerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState(0);

  function autoResizeTextarea() {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${element.scrollHeight}px`;
  }

  const showSuggestions = useMemo(() => {
    const trimmed = value.trim();
    if (!trimmed) return true;
    return examples.some((example) => example.toLowerCase() === trimmed.toLowerCase());
  }, [examples, value]);

  useEffect(() => {
    if (!showSuggestions) {
      setSelectedSuggestion(0);
    }
  }, [showSuggestions]);

  useEffect(() => {
    autoResizeTextarea();
  }, [value]);

  function confirmSuggestion(index: number) {
    if (index < 0 || index >= examples.length) return;
    onChange(examples[index]);
    requestAnimationFrame(() => {
      textareaRef.current?.focus();
      textareaRef.current?.setSelectionRange(
        examples[index].length,
        examples[index].length,
      );
    });
  }

  function onEditorKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!showSuggestions || examples.length === 0) return;

    if (event.key === "Tab") {
      event.preventDefault();
      const direction = event.shiftKey ? -1 : 1;
      const next =
        (selectedSuggestion + direction + examples.length) % examples.length;
      setSelectedSuggestion(next);
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      confirmSuggestion(selectedSuggestion);
    }
  }

  return (
    <div className="space-y-3">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onEditorKeyDown}
        disabled={disabled}
        rows={4}
        className="w-full min-h-[150px] resize-none overflow-hidden rounded-xl border border-border bg-panelAlt px-3 py-3 text-sm text-textMain outline-none transition focus:border-accent/60 disabled:cursor-not-allowed disabled:opacity-70"
        placeholder="Example: For every natural number n, n + 0 = n."
      />

      <ExampleSuggestions
        visible={showSuggestions}
        examples={examples}
        selectedIndex={selectedSuggestion}
        onSelectIndex={setSelectedSuggestion}
        onConfirmIndex={confirmSuggestion}
      />
    </div>
  );
}

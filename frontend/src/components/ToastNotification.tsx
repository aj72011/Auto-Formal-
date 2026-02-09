import { AnimatePresence, motion } from "framer-motion";

interface ToastNotificationProps {
  visible: boolean;
  message: string;
}

export function ToastNotification({ visible, message }: ToastNotificationProps) {
  return (
    <AnimatePresence>
      {visible ? (
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          transition={{ duration: 0.18 }}
          className="fixed bottom-5 right-5 z-50 rounded-md border border-border bg-panel px-3 py-2 text-xs text-textMain shadow-sm"
          role="status"
          aria-live="polite"
        >
          {message}
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

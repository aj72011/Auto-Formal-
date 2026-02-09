import { AnimatePresence, motion } from "framer-motion";
import { ReactNode } from "react";

interface PageTransitionContainerProps {
  pageKey: string;
  direction: 1 | -1;
  children: ReactNode;
}

export function PageTransitionContainer({
  pageKey,
  direction,
  children,
}: PageTransitionContainerProps) {
  return (
    <div className="relative h-full w-full overflow-hidden">
      <AnimatePresence custom={direction} initial={false} mode="wait">
        <motion.div
          key={pageKey}
          custom={direction}
          className="absolute inset-0 h-full w-full"
          variants={{
            enter: (d: 1 | -1) => ({
              x: d > 0 ? "100%" : "-100%",
              opacity: 0.25,
            }),
            center: {
              x: "0%",
              opacity: 1,
            },
            exit: (d: 1 | -1) => ({
              x: d > 0 ? "-30%" : "30%",
              opacity: 0.12,
            }),
          }}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{
            duration: 0.42,
            ease: [0.22, 1, 0.36, 1],
          }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

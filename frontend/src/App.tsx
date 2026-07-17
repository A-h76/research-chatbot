import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { MotionConfig } from "framer-motion";
import { queryClient } from "@/lib/queryClient";
import { ThemeProvider } from "@/context/ThemeContext";
import { UIProvider } from "@/context/UIContext";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { CookieConsent } from "@/components/common/CookieConsent";
import { router } from "@/routes/router";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <UIProvider>
          <TooltipProvider>
            {/* reducedMotion="user" respects prefers-reduced-motion. */}
            <MotionConfig reducedMotion="user">
              <RouterProvider router={router} />
              <CookieConsent />
              <Toaster position="bottom-center" />
            </MotionConfig>
          </TooltipProvider>
        </UIProvider>
      </ThemeProvider>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}

export default App;

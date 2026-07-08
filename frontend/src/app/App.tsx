import { QueryClientProvider } from "@tanstack/react-query";

import { AppRouter } from "./AppRouter";
import { AuthProvider } from "./auth";
import { createAppQueryClient } from "./queryClient";

const queryClient = createAppQueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </QueryClientProvider>
  );
}

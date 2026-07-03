import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AppRouter } from "./AppRouter";
import { AuthProvider } from "./auth";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </QueryClientProvider>
  );
}

import { useQuery } from "@tanstack/react-query";

import { empresasClient } from "../../lib/api/empresasClient";
import { queryKeys } from "../../lib/queryKeys";

const empresasAutorizadasQueryKey = queryKeys.empresas.autorizadas();

export function useEmpresasAutorizadasQuery(accessToken: string) {
  const query = useQuery({
    queryKey: empresasAutorizadasQueryKey,
    queryFn: () => empresasClient.list(accessToken),
    enabled: Boolean(accessToken),
  });

  return {
    ...query,
    queryKey: empresasAutorizadasQueryKey,
  };
}

import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

/** Plan kapsamı: aile kimliği ?aile=... ile tutulur; yoksa kişisel plan. */
export function useScope() {
  const [params, setParams] = useSearchParams();
  const familyId = params.get("aile");

  const setFamilyId = useCallback(
    (id: string | null) => {
      const next = new URLSearchParams(params);
      if (id) next.set("aile", id);
      else next.delete("aile");
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  return { familyId, setFamilyId };
}

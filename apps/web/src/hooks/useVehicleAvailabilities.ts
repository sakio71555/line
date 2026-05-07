import { useCallback, useEffect, useState } from "react";

import { fetchVehicleAvailabilities, type VehicleAvailabilityItem } from "../lib/liffApi";

export function useVehicleAvailabilities() {
  const [vehicleAvailabilities, setVehicleAvailabilities] = useState<VehicleAvailabilityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVehicleAvailabilities(100);
      setVehicleAvailabilities(data.vehicle_availabilities);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "空車一覧の取得に失敗しました。");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    vehicleAvailabilities,
    loading,
    error,
    reload: load,
  };
}


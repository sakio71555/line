export const vehicleTypeOptions = [
  "軽バン",
  "冷蔵軽貨物",
  "2t",
  "4t",
  "10t",
  "トレーラー",
  "その他",
] as const;

export type VehicleTypeOption = (typeof vehicleTypeOptions)[number];

export function isVehicleTypeOption(value: string): value is VehicleTypeOption {
  return vehicleTypeOptions.includes(value as VehicleTypeOption);
}

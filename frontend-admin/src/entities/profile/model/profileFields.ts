export const coreProfileFields = [
  "Фамилия",
  "Имя",
  "Отчество",
  "Подтверждённый телефон",
  "Электронная почта",
  "Дата рождения",
] as const;

export const coreProfileKeys = new Set([
  "last_name",
  "first_name",
  "patronymic",
  "phone",
  "phone_verified",
  "email",
  "birth_date",
]);

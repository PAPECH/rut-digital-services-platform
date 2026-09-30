import type { Profile, ProfileFieldDefinition } from "@/api/types";
import {
  getMissingProfileFields,
  isMissing,
  profileValue,
} from "@/features/profile-requirements/model/profileRequirements";

const TEST_ONLY_REQUIREMENTS = [
  ["birth_date", "Дата рождения"],
  ["email", "Электронная почта"],
] as const;

/** `form_tests`-only requirement layered on top of the shared profile check (Task 080) -- birth
 * date and email stay optional everywhere else (`modules/forms`, the profile screen itself); a
 * student must have both to start or resume a test, since the platform now sources them from the
 * profile instead of asking as test questions. */
export function getMissingTestProfileFields(
  profile: Profile | null | undefined,
  schema: ProfileFieldDefinition[] | undefined,
): string[] {
  const missing = getMissingProfileFields(profile, schema);
  if (!profile) return missing;
  const extra = TEST_ONLY_REQUIREMENTS.filter(([key]) => isMissing(profileValue(profile, key))).map(
    ([, label]) => label,
  );
  return [...new Set([...missing, ...extra])];
}

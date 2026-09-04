export async function getCases() {
  const res = await fetch("/cases?limit=100");
  return res.json();
}

export async function getCase(id) {
  const res = await fetch(`/cases/${id}`);
  if (!res.ok) return null;
  return res.json();
}

export function getCaseAudioUrl(id) {
  return `/cases/${id}/audio`;
}

export async function postReview(id, analystAction, note) {
  const form = new FormData();
  form.set("analyst_action", analystAction);
  form.set("note", note || "");
  const res = await fetch(`/cases/${id}/review`, { method: "POST", body: form });
  return res.json();
}

export async function postEnroll(ownerId, audioBlob) {
  const form = new FormData();
  form.set("owner_id", ownerId);
  form.set("audio", audioBlob, "reference.wav");
  const res = await fetch("/enroll", { method: "POST", body: form });
  return res.json();
}

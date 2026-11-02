import { getSql } from "@/lib/db";

function asBool(value: unknown): boolean {
  return value === true || value === "t" || value === "true" || value === 1;
}

export async function readEnabled(): Promise<boolean> {
  const sql = await getSql();
  const rows = await sql<{ enabled: unknown }>`select enabled from keel_switch where id = 1`;
  const row = rows[0];
  if (!row) return true;
  return asBool(row.enabled);
}

export async function writeEnabled(enabled: boolean): Promise<boolean> {
  const sql = await getSql();
  await sql`
    insert into keel_switch (id, enabled)
    values (1, ${enabled})
    on conflict (id) do update set enabled = ${enabled}
  `;
  return enabled;
}

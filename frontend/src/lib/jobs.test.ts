import { describe, expect, it } from "vitest";
import { recoveryMessage } from "./jobs";
describe("durable job outcome wording",()=>{
  it.each(["RECONCILIATION_REQUIRED","DEAD_LETTERED","RUNNING","COMPLETED","QUEUED"])("explains %s without fabricating state",status=>{
    const message=recoveryMessage(status);
    expect(message.length).toBeGreaterThan(5);
    if(status==="RECONCILIATION_REQUIRED") expect(message).toContain("No blind retry");
    if(status==="RUNNING") expect(message).toContain("cannot promise rollback");
  });
});

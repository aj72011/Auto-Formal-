import { AppWorkspaceController } from "./workspace/AppWorkspaceController";
import { VerificationStateManager } from "./state/VerificationStateManager";

export default function App() {
  return (
    <VerificationStateManager>
      <AppWorkspaceController />
    </VerificationStateManager>
  );
}

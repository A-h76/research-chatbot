import { useParams } from "react-router-dom";
import { useMe } from "@/features/profile/useMe";
import { WelcomeView } from "../components/WelcomeView";
import { ConversationView } from "../components/ConversationView";

export function ChatPage() {
  const { conversationId } = useParams();
  const { data: me } = useMe();

  if (conversationId) {
    return <ConversationView key={conversationId} conversationId={Number(conversationId)} />;
  }
  if (!me) return null;
  return <WelcomeView me={me} />;
}

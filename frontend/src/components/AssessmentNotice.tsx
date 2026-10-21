import { notice,useResultLanguage } from '../services/resultLanguage.ts';
export function AssessmentNotice() {
  const {language}=useResultLanguage();
  return <aside className="assessment-notice" aria-label="Assessment limits">
    {notice(language)}
  </aside>;
}

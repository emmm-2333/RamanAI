/**
 * 拉曼诊断系统医学术语翻译 composable
 * 统一管理所有英文→中文的映射，避免各组件重复定义
 */
export function useTranslations() {
  const markerMap = {
    ER: "ER (雌激素受体)",
    PR: "PR (孕激素受体)",
    HER2: "HER2 (人表皮生长因子受体2)",
    Ki67: "Ki67 (细胞增殖指数)",
  };

  const statusMap = {
    Positive: "阳性",
    Negative: "阴性",
    High: "高表达",
    Low: "低表达",
  };

  const diagnosisMap = {
    Malignant: "恶性",
    Benign: "良性",
    Unknown: "未知",
  };

  const translateMarker = (key) => markerMap[key] ?? key;
  const translateStatus = (val) => statusMap[val] ?? val;
  const translateDiagnosis = (val) => diagnosisMap[val] ?? val;

  return { translateMarker, translateStatus, translateDiagnosis };
}

import api from "./index";

export default {
  getModels() {
    return api.get("models/");
  },

  trainModel(params) {
    // params: { description, algorithm, test_size, n_estimators }
    return api.post("models/", { action: "train", ...params });
  },
};

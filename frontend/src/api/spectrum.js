import api from "./index";

export default {
  // Get list of records
  getRecords(params) {
    return api.get("records/", { params });
  },

  getRecord(id) {
    return api.get(`records/${id}/`);
  },

  preprocessRecord(id, config) {
    return api.post(`records/${id}/preprocess/`, { config });
  },

  uploadSpectrum(formData) {
    return api.post("upload/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  batchUploadSpectrum(formData) {
    return api.post("upload/batch/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  submitFeedback(data) {
    return api.post("feedback/", data);
  },
};

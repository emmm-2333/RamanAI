import api from './index';

export default {
  // Get list of records
  getRecords(params) {
    return api.get('upload/', { params }); // Assuming backend supports GET /upload/ or similar for list
    // Note: Current backend implementation of UploadView only handles POST.
    // We might need to add GET method to UploadView or a new ListView.
    // Let's assume we will add a ListAPIView for records.
  },
  
  getRecord(id) {
    return api.get(`records/${id}/`);
  },

  preprocessRecord(id, config) {
    return api.post(`records/${id}/preprocess/`, { config });
  },

  uploadSpectrum(formData) {
    return api.post('upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  submitFeedback(data) {
    return api.post('feedback/', data);
  }
};

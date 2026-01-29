import api from './index';

export default {
  getModels() {
    return api.get('models/');
  },
  
  trainModel(description) {
    return api.post('models/', { action: 'train', description });
  }
};

import api from './index';

export default {
  getPCAData() {
    return api.get('analysis/pca/');
  }
};

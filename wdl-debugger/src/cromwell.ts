import { createReadStream } from 'fs';
import { get, post } from 'request-promise-native';

export type WorkflowResponse = {
  id: string;
  status: string;
};

export const postWorkflow = async (
  baseUri: string,
  wdlPath: string,
  inputsPath: string,
  optionsPath: string,
): Promise<WorkflowResponse> => {
  return post(baseUri, {
    json: true,
    formData: {
      workflowSource: createReadStream(wdlPath),
      workflowInputs: createReadStream(inputsPath),
      workflowOptions: createReadStream(optionsPath),
    },
  });
};

export const getWorklowStatus = async (
  baseUri: string,
  id: string,
): Promise<WorkflowResponse> => {
  return get(`${baseUri}/${id}/status`, {
    json: true,
  });
};

export const abortWorkflow = async (
  baseUri: string,
  id: string,
): Promise<WorkflowResponse> => {
  return post(`${baseUri}/${id}/abort`, {
    json: true,
  });
};

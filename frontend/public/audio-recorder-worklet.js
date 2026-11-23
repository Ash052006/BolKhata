/**
 * AudioWorkletProcessor for capturing 16,000 Hz, 16-bit mono signed little-endian PCM.
 *
 * Runs off the main browser thread to guarantee glitch-free, uninterrupted audio streaming.
 */

class PCMRecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.targetSampleRate = 16000
    this.bufferSize = 800 // 50ms at 16kHz
    this.buffer = new Int16Array(this.bufferSize)
    this.bufferIndex = 0
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || input.length === 0) {
      return true
    }

    const channelData = input[0]
    if (!channelData || channelData.length === 0) {
      return true
    }

    // Downsample / resample linearly if context sample rate differs from target 16kHz
    const inputSampleRate = currentFrame ? sampleRate : 16000
    const ratio = inputSampleRate / this.targetSampleRate

    if (Math.abs(ratio - 1.0) < 0.01) {
      // 1:1 direct sampling
      for (let i = 0; i < channelData.length; i++) {
        const s = Math.max(-1, Math.min(1, channelData[i]))
        // Scale to signed 16-bit integer
        this.buffer[this.bufferIndex++] = s < 0 ? s * 0x8000 : s * 0x7fff
        if (this.bufferIndex >= this.bufferSize) {
          this.flush()
        }
      }
    } else {
      // Linear resampling step
      let inputIndex = 0
      while (inputIndex < channelData.length) {
        const s = Math.max(-1, Math.min(1, channelData[Math.floor(inputIndex)]))
        this.buffer[this.bufferIndex++] = s < 0 ? s * 0x8000 : s * 0x7fff
        if (this.bufferIndex >= this.bufferSize) {
          this.flush()
        }
        inputIndex += ratio
      }
    }

    return true
  }

  flush() {
    if (this.bufferIndex === 0) return
    const chunk = this.buffer.slice(0, this.bufferIndex)
    this.port.postMessage(chunk.buffer, [chunk.buffer])
    this.buffer = new Int16Array(this.bufferSize)
    this.bufferIndex = 0
  }
}

registerProcessor('pcm-recorder-processor', PCMRecorderProcessor)

const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

const isProduction = process.env.NODE_ENV === 'production';

const cssLoaders = [
  isProduction ? MiniCssExtractPlugin.loader : 'style-loader',
  'css-loader',
  'postcss-loader',
  'sass-loader'
];

module.exports = {
  mode: isProduction ? 'production' : 'development',
  devtool: isProduction ? 'source-map' : 'eval-source-map',

  entry: {
    app: './app/static/js/app.js',
    dashboard: './app/static/js/pages/dashboard.js',
    analytics: './app/static/js/pages/analytics.js',
    sales: './app/static/js/pages/sales.js'
  },

  output: {
    path: path.resolve(__dirname, 'app/static/dist'),
    filename: 'js/[name].js',
    publicPath: '/static/'
  },

  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        parser: {
          javascript: {
            sourceType: 'module'
          }
        },
        type: 'javascript/esm',
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env'],
            sourceType: 'module',
            parserOpts: {
              sourceType: 'module'
            }
          }
        }
      },
      {
        test: /\.(sa|sc|c)ss$/,
        use: cssLoaders
      },
      {
        test: /\.(png|jpe?g|gif|svg|woff2?|eot|ttf|otf)$/,
        type: 'asset/resource',
        generator: {
          filename: 'assets/[hash][ext][query]'
        }
      }
    ]
  },

  plugins: [
    new MiniCssExtractPlugin({
      filename: 'css/[name].css',
      chunkFilename: 'css/[id].css'
    }),
    new CopyWebpackPlugin({
      patterns: [
        {
          from: 'app/static/img',
          to: 'img',
          noErrorOnMissing: true
        },
        {
          from: 'app/static/fonts',
          to: 'fonts',
          noErrorOnMissing: true
        }
      ]
    })
  ],

  resolve: {
    extensions: ['.js', '.json', '.scss'],
    alias: {
      '@js': path.resolve(__dirname, 'app/static/js'),
      '@styles': path.resolve(__dirname, 'app/static/scss')
    }
  },

  optimization: {
    splitChunks: {
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all'
        }
      }
    }
  },

  performance: {
    hints: isProduction ? 'warning' : false,
    maxEntrypointSize: 512000,
    maxAssetSize: 512000
  }
};
